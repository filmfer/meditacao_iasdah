const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const fs = require('fs');

let qrTimeout;

// Flag de encerramento controlado: quando true, o handler 'disconnected'
// não deve interpretar o fecho intencional (client.destroy()) como falha.
let finalizando = false;

// ------------------------------------------------------------
// MODO DE PAREAMENTO (testes / recuperação de sessão)
// ------------------------------------------------------------
// Ativar com: WHATSAPP_PAREAMENTO=1 node send_whatsapp.js
// Executa APENAS a autenticação: desenha o QR Code no terminal para
// associar um novo dispositivo e, depois de lido, persiste a sessão
// em ./whatsapp_auth e sai com sucesso. NÃO exige whatsapp_msg.txt
// nem WHATSAPP_GROUP_ID — útil quando o artefacto whatsapp-session
// se perdeu e é preciso religar o bot ao WhatsApp.
const MODO_PAREAMENTO = process.env.WHATSAPP_PAREAMENTO === '1';

// Mensagens finais de motivação para a leitura diária (uma é escolhida
// aleatoriamente em cada execução). Enviada após a última meditação.
const MOTIVACOES = [
    '🌅✨ E com isto terminamos as meditações de hoje!\n\n📖 Reserve um momento tranquilo para a leitura diária — "a tua palavra é lâmpada para os meus pés e luz para o meu caminho" (Salmo 119:105). 🙏\n\nBom dia abençoado! 💛',
    '☀️🙏 As meditações de hoje já estão no grupo!\n\n📚 Um pouquinho da Palavra de manhã transforma o dia inteiro. Não te esqueças da leitura de hoje! 📖✨\n\nTenha um ótimo dia! 💛',
    '🌱💛 Três meditações, três oportunidades de crescer hoje!\n\n✝️ Completa o dia com a leitura diária — os pequenos momentos com Deus fazem toda a diferença. 📖🔥\n\nUm dia abençoado para todos! ☀️'
];

// ------------------------------------------------------------
// MINIATURA DO YOUTUBE
// ------------------------------------------------------------
// O WhatsApp só gera preview de links via a opção linkPreview da
// biblioteca, que é notoriamente instável. Solução determinística:
// descarregar a miniatura do vídeo (img.youtube.com) e enviá-la como
// imagem com o link na caption. Nota: o WhatsApp não suporta imagens
// clicáveis — o redirecionamento para o vídeo faz-se pela caption.

const VIDEO_ID_RE = /watch\?v=([A-Za-z0-9_-]{5,20})/;

function extrairVideoId(texto) {
    const m = texto.match(VIDEO_ID_RE);
    return m ? m[1] : null;
}

// Descarrega a miniatura do vídeo. Tenta maxresdefault (1280x720) e
// faz fallback para hqdefault (480x360, existe sempre). Devolve um
// objeto compatível com MessageMedia ou null se falhar.
async function descarregarMiniatura(videoId) {
    const qualidades = ['maxresdefault', 'hqdefault'];
    for (const qualidade of qualidades) {
        const url = `https://img.youtube.com/vi/${videoId}/${qualidade}.jpg`;
        try {
            // AbortSignal.timeout: nunca deixar o fetch suspenso o job.
            const res = await fetch(url, { signal: AbortSignal.timeout(10000) });
            if (!res.ok) {
                console.log(`Miniatura ${qualidade} indisponível (HTTP ${res.status}) para ${videoId}.`);
                continue;
            }
            const buf = Buffer.from(await res.arrayBuffer());
            // A maxresdefault pode existir fisicamente mas ser o placeholder
            // cinzento de 120x90 (~1KB); nesse caso, passar à qualidade seguinte.
            if (buf.length < 2000) {
                console.log(`Miniatura ${qualidade} é placeholder vazio para ${videoId}.`);
                continue;
            }
            console.log(`Miniatura ${qualidade} obtida (${buf.length} bytes) para ${videoId}.`);
            return { mime: 'image/jpeg', data: buf.toString('base64'), filename: `thumb_${videoId}.jpg` };
        } catch (err) {
            console.error(`Falha ao descarregar miniatura ${qualidade} para ${videoId}:`, err.message || err);
        }
    }
    return null;
}

const client = new Client({
    authStrategy: new LocalAuth({
        dataPath: './whatsapp_auth' 
    }),
    puppeteer: {
        headless: true,
        args: [
            '--no-sandbox', 
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage', 
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu'
        ]
    },
    // webVersionCache pin RESTAURADO (2026-09-06): o WhatsApp passou a
    // servir uma versão que o mecanismo default da biblioteca não consegue
    // carregar — o boot do WhatsApp Web fica suspenso antes de gerar QR
    // ("Nem 'qr' nem 'ready' disparado em 90s"), exactamente a falha do
    // run de 2026-09-06 20:03 UTC. O pin aponta para a versão CURRENT
    // listada em https://wppconnect.io/whatsapp-versions (validade ~2
    // meses: 2.3000.1046922887-alpha expira a 2026-11-06). Quando este
    // erro voltar a aparecer, actualizar o remotePath para a nova versão
    // current dessa página — nunca deixar um pin expirado no lugar.
    webVersionCache: {
        type: 'remote',
        remotePath: 'https://raw.githubusercontent.com/wppconnect-team/wa-version/main/html/2.3000.1046922887-alpha.html'
    }
});

// Global watchdog: if neither 'qr' nor 'ready' fires at all (e.g. because
// WhatsApp's servers silently reject/hang the connection), the process
// used to hang until the GitHub Actions job timeout with zero signal.
// This forces a fast, loud failure so alert_failure.py actually runs today.
// Em vez de falhar à primeira, REINICIALIZA o cliente até MAX_TENTATIVAS_INIT
// vezes (90s cada): bloqueios transitórios de rede/boot resolvem-se num
// reboot da página, sem gastar o run inteiro.
const MAX_TENTATIVAS_INIT = 3;
let tentativasInit = 0;
let initWatchdog = null;

function armarWatchdogInit() {
    return setTimeout(async () => {
        tentativasInit++;
        if (tentativasInit >= MAX_TENTATIVAS_INIT) {
            console.error(`Abort: Nem "qr" nem "ready" disparados após ${MAX_TENTATIVAS_INIT} tentativas de 90s. Provável incompatibilidade de versão do WhatsApp Web (actualizar o webVersionCache com a versão current de https://wppconnect.io/whatsapp-versions) ou falha de rede.`);
            client.destroy();
            process.exit(1);
        }
        console.error(`Aviso: nem "qr" nem "ready" em 90s (tentativa ${tentativasInit}/${MAX_TENTATIVAS_INIT - 1}). A reinicializar o cliente...`);
        try {
            await Promise.race([
                client.destroy(),
                new Promise(resolve => setTimeout(resolve, 15000))
            ]);
        } catch (err) {
            console.error('Aviso: erro durante client.destroy() na reinicialização (não-fatal):', err.message || err);
        }
        try {
            client.initialize();
        } catch (err) {
            console.error('Erro fatal ao reinicializar o cliente:', err.message || err);
            process.exit(1);
        }
        initWatchdog = armarWatchdogInit();
    }, 90000);
}

initWatchdog = armarWatchdogInit();

client.on('qr', (qr) => {
    clearTimeout(initWatchdog);
    if (qrTimeout) clearTimeout(qrTimeout); // don't stack timers if 'qr' auto-refreshes
    if (MODO_PAREAMENTO) {
        console.error('Modo de pareamento: novo QR Code gerado.');
        console.error('Abre o WhatsApp no telemóvel (Definições > Dispositivos ligados > Ligar um dispositivo) e aponta a câmara para o QR abaixo.');
    } else {
        console.error('AVISO: Sessão expirou. Novo QR Code gerado.');
    }
    require('qrcode-terminal').generate(qr, { small: true, inverse: true });
    
    // Gives you a realistic window to open the live log + WhatsApp on your
    // phone + scan. 90s was too tight once you account for GH Actions'
    // own log-streaming lag; 5 minutes gives real breathing room.
    qrTimeout = setTimeout(() => { 
        console.error('Abort: QR Code não foi lido a tempo.');
        client.destroy(); 
        process.exit(1); 
    }, 300000);
});

client.on('disconnected', (reason) => {
    console.error('Sessão desconectada pelo WhatsApp:', reason);
    if (finalizando) {
        console.log('Desconexão esperada: encerramento controlado do cliente.');
        return;
    }
    process.exit(1);
});

client.on('ready', async () => {
    // Cancel any pending self-destruct timeouts now that we're fully authenticated
    clearTimeout(initWatchdog);
    if (qrTimeout) {
        clearTimeout(qrTimeout);
    }

    console.log('WhatsApp Client connection established successfully!');

    // ------------------------------------------------------------
    // MODO DE PAREAMENTO: autenticar, guardar a sessão e sair.
    // ------------------------------------------------------------
    // Não lê payload, não envia mensagens, não precisa do grupo.
    // A espera de 15s dá tempo ao LocalAuth sincronizar o estado da
    // sessão para ./whatsapp_auth antes do destroy().
    if (MODO_PAREAMENTO) {
        console.log('✅ Autenticado com sucesso — sessão nova válida.');
        console.log('A aguardar 15 segundos para o LocalAuth persistir a sessão em ./whatsapp_auth ...');
        await new Promise(resolve => setTimeout(resolve, 15000));

        finalizando = true;
        try {
            await Promise.race([
                client.destroy(),
                new Promise(resolve => setTimeout(() => {
                    console.error('Aviso: client.destroy() demorou mais de 15s; a forçar a saída.');
                    resolve();
                }, 15000))
            ]);
            console.log('Sessão guardada em ./whatsapp_auth. Pareamento concluído com sucesso.');
        } catch (err) {
            console.error('Aviso: erro durante client.destroy() (não-fatal):', err.message || err);
        }
        process.exit(0);
    }

    console.log('A aguardar 20 segundos para estabilização inicial e sincronização de chats...');
    await new Promise(resolve => setTimeout(resolve, 20000));
    
    if (!fs.existsSync('whatsapp_msg.txt')) {
        console.error('Abort: whatsapp_msg.txt not found.');
        client.destroy();
        process.exit(1);
    }

    const rawContent = fs.readFileSync('whatsapp_msg.txt', 'utf8');
    
    const mensagens = rawContent.split('===DIVISAO_MEDITACAO===')
                                .map(msg => msg.trim())
                                .filter(msg => msg.length > 0);

    if (mensagens.length === 0) {
        console.error('Abort: Nenhuma meditação válida encontrada no payload.');
        client.destroy();
        process.exit(1);
    }

    let groupId = process.env.WHATSAPP_GROUP_ID;
    if (!groupId) {
        console.error('Abort: WHATSAPP_GROUP_ID is missing.');
        client.destroy();
        process.exit(1);
    }
    groupId = groupId.trim().replace(/['"]/g, ''); 

    try {
        console.log(`Grupo alvo: ${groupId}`);
        // NOTE: intentionally NOT calling client.getChatById() here.
        // whatsapp-web.js currently has an active, unresolved bug where
        // getChatById crashes with a terse "r" error on the current
        // WhatsApp Web rollout (upstream issue #201838, still open as of
        // this writing) — it hydrates a full Chat model via a heavier
        // internal path that's breaking for many people right now.
        // client.sendMessage() takes a chat ID directly and uses a
        // lighter internal lookup that avoids that code path entirely.

        // Send each meditation independently: one failing (thrown OR
        // silently swallowed by WhatsApp) shouldn't block the others,
        // and we want a clear per-message pass/fail report instead of
        // a silent drop leaving zero trace in the log.
        const resultados = [];

        for (let i = 0; i < mensagens.length; i++) {
            const numero = i + 1;
            console.log(`\nA processar publicação ${numero} de ${mensagens.length}...`);

            // Clean markdown escapes. Covers the FULL Telegram MarkdownV2
            // escape set (_*[]()~`>#+-=|{}.!) as a safety net — the real
            // fix is that meditacao_iasdah.py now writes the already-clean
            // whatsapp_content instead of the escaped telegram_content,
            // but this stays defensive in case that ever regresses.
            let mensagemLimpa = mensagens[i].replace(/\\([_*[\]()~`>#+\-=|{}.!])/g, '$1');

            // --------------------------------------------------------
            // MINIATURA DO YOUTUBE + TEXTO NUMA ÚNICA MENSAGEM
            // --------------------------------------------------------
            // Cada meditação é publicada como UMA mensagem: a imagem do
            // vídeo (aparece primeiro) e, por baixo, na caption, o título,
            // o texto e os links finais da meditação. O WhatsApp não gera
            // preview de links de forma fiável; a imagem garante o thumbnail
            // visual e o link do YouTube na caption continua clicável.
            //
            // A caption de mídia tem um limite prático de ~1024 caracteres
            // (documentado na Cloud API; no Web, o excesso é truncado
            // silenciosamente). Textos acima do limite seguem logo o
            // caminho de recurso: miniatura com legenda curta + texto numa
            // mensagem própria — para nunca circular texto cortado.
            const LIMITE_CAPTION = 1024;
            let miniatura = null;
            const videoId = extrairVideoId(mensagemLimpa);
            if (videoId) {
                try {
                    miniatura = await descarregarMiniatura(videoId);
                    if (!miniatura) {
                        console.log(`Sem miniatura disponível para a meditação ${numero}; envio apenas o texto.`);
                    }
                } catch (err) {
                    console.error(`Erro inesperado no processamento da miniatura ${numero} (não-fatal):`, err.message || err);
                }
            }

            const usaMensagemUnica = Boolean(miniatura) && mensagemLimpa.length <= LIMITE_CAPTION;
            if (miniatura && !usaMensagemUnica) {
                console.log(`Texto da meditação ${numero} tem ${mensagemLimpa.length} caracteres (limite de caption: ${LIMITE_CAPTION}); a miniatura segue com legenda curta e o texto numa mensagem separada.`);
            }

            let enviado = false;
            let ultimoErro = null;

            for (let tentativa = 1; tentativa <= 2 && !enviado; tentativa++) {
                try {
                    if (miniatura && tentativa === 1 && usaMensagemUnica) {
                        // CAMINHO PRINCIPAL: mensagem ÚNICA — a imagem do
                        // vídeo aparece primeiro e a caption traz o título,
                        // o texto e os links finais da meditação.
                        const thumb = new MessageMedia(miniatura.mime, miniatura.data, miniatura.filename);
                        await client.sendMessage(groupId, thumb, { caption: mensagemLimpa });
                        enviado = true;
                        console.log(`Mensagem única ${numero} enviada (miniatura do vídeo + título/texto/links na caption) — tentativa ${tentativa}.`);
                    } else if (miniatura) {
                        // FALLBACK: legenda curta na imagem e o texto numa
                        // mensagem própria (usado quando o texto excede o
                        // limite de caption ou a mensagem única falhou).
                        const thumb = new MessageMedia(miniatura.mime, miniatura.data, miniatura.filename);
                        const captionCurta = `🎬 Ver o vídeo da meditação:\nhttps://www.youtube.com/watch?v=${videoId}`;
                        await client.sendMessage(groupId, thumb, { caption: captionCurta });
                        console.log(`🖼️ Miniatura da meditação ${numero} enviada com legenda curta (fallback).`);
                        await client.sendMessage(groupId, mensagemLimpa);
                        enviado = true;
                        console.log(`Mensagem ${numero} (texto) enviada a seguir à miniatura — tentativa ${tentativa}.`);
                    } else {
                        await client.sendMessage(groupId, mensagemLimpa);
                        enviado = true;
                        console.log(`Mensagem ${numero} enviada (tentativa ${tentativa}) — chamada resolvida sem erro.`);
                    }
                } catch (err) {
                    ultimoErro = err.message || String(err);
                    console.error(`Falha ao enviar mensagem ${numero} (tentativa ${tentativa}):`, ultimoErro);
                    if (tentativa < 2) {
                        if (miniatura && usaMensagemUnica) {
                            console.log('A preparar o fallback em duas mensagens (imagem + texto) para a próxima tentativa...');
                        }
                        console.log('A aguardar 15 segundos antes de tentar novamente...');
                        await new Promise(resolve => setTimeout(resolve, 15000));
                    }
                }
            }

            resultados.push({ numero, enviado, erro: ultimoErro });

            if (i < mensagens.length - 1) {
                console.log('⏱️ Aguarda 20 segundos antes da próxima publicação...');
                await new Promise(resolve => setTimeout(resolve, 20000));
            }
        }

        console.log('\n--- Resumo do envio ---');
        resultados.forEach(r => {
            console.log(r.enviado
                ? `✅ Mensagem ${r.numero}: enviada (sem erro reportado)`
                : `❌ Mensagem ${r.numero}: FALHOU — ${r.erro}`);
        });
        console.log('NOTA: "enviada" só confirma que a chamada não lançou erro — se o');
        console.log('WhatsApp descartar a mensagem silenciosamente (bug conhecido da');
        console.log('biblioteca em grupos após a atualização de julho/2026), aqui vai');
        console.log('aparecer como sucesso mesmo assim. Confirma sempre no grupo.');

        const houveFalha = resultados.some(r => !r.enviado);

        // ------------------------------------------------------------
        // MENSAGEM FINAL DE MOTIVAÇÃO
        // ------------------------------------------------------------
        // Além do valor devocional, atua como período de tolerância para a
        // ÚLTIMA meditação: o sendMessage() resolve a Promise quando a
        // mensagem é aceite pela camada interna, mas a entrega real ao grupo
        // precisa da ligação viva mais alguns segundos. O destroy() imediato
        // após o último envio matava essa entrega — era por isso que a 3ª
        // meditação nunca chegava ao grupo. Os 20s de espera + a própria
        // mensagem de motivação garantem esse intervalo.
        console.log('\n⏱️ Aguarda 20 segundos antes da mensagem final de motivação...');
        await new Promise(resolve => setTimeout(resolve, 20000));

        try {
            const motivacao = MOTIVACOES[Math.floor(Math.random() * MOTIVACOES.length)];
            await client.sendMessage(groupId, motivacao);
            console.log('✅ Mensagem de motivação enviada.');
        } catch (err) {
            // Não-fatal: a motivação é um extra e nunca deve marcar o job
            // como falhado nem disparar o alerta de sessão expirada.
            console.error('⚠️ Falha ao enviar a mensagem de motivação (não-fatal):', err.message || err);
        }

        // ------------------------------------------------------------
        // ENCERRAMENTO CONTROLADO
        // ------------------------------------------------------------
        // Espera de 5s para a mensagem de motivação ser entregue e para o
        // LocalAuth sincronizar o estado da sessão em disco, seguido de um
        // destroy() efetivamente aguardado (com teto de 15s para o caso do
        // Puppeteer congelar no teardown e suspender o job até ao timeout).
        finalizando = true;
        console.log('\nA aguardar 5 segundos antes de encerrar o cliente...');
        await new Promise(resolve => setTimeout(resolve, 5000));

        try {
            await Promise.race([
                client.destroy(),
                new Promise(resolve => setTimeout(() => {
                    console.error('Aviso: client.destroy() demorou mais de 15s; a forçar a saída.');
                    resolve();
                }, 15000))
            ]);
            console.log('Cliente WhatsApp encerrado corretamente.');
        } catch (err) {
            console.error('Aviso: erro durante client.destroy() (não-fatal):', err.message || err);
        }
        process.exit(houveFalha ? 1 : 0);

    } catch (err) {
        console.error('Erro fatal no processamento:', err.message || err);
        finalizando = true;
        client.destroy();
        process.exit(1); 
    }
});

client.on('auth_failure', (msg) => {
    console.error('Falha na assinatura de autenticação:', msg);
    process.exit(1);
});

client.initialize();
