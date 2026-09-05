const { Client, LocalAuth } = require('whatsapp-web.js');
const fs = require('fs');

let qrTimeout;

// Flag de encerramento controlado: quando true, o handler 'disconnected'
// não deve interpretar o fecho intencional (client.destroy()) como falha.
let finalizando = false;

// Mensagens finais de motivação para a leitura diária (uma é escolhida
// aleatoriamente em cada execução). Enviada após a última meditação.
const MOTIVACOES = [
    '🌅✨ E com isto terminamos as meditações de hoje!\n\n📖 Reserve um momento tranquilo para a leitura diária — "a tua palavra é lâmpada para os meus pés e luz para o meu caminho" (Salmo 119:105). 🙏\n\nBom dia abençoado! 💛',
    '☀️🙏 As meditações de hoje já estão no grupo!\n\n📚 Um pouquinho da Palavra de manhã transforma o dia inteiro. Não te esqueças da leitura de hoje! 📖✨\n\nTenha um ótimo dia! 💛',
    '🌱💛 Três meditações, três oportunidades de crescer hoje!\n\n✝️ Completa o dia com a leitura diária — os pequenos momentos com Deus fazem toda a diferença. 📖🔥\n\nUm dia abençoado para todos! ☀️'
];

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
    }
    // NOTE: webVersionCache pin REMOVED on purpose (see incident writeup).
    // It was hardcoded to WhatsApp Web version 2.2412.54 (~Dec 2024).
    // WhatsApp now runs the 2.3000.xxxxxxxxxx-alpha version line and
    // *expires every pinned version ~2 months after release* (confirmed
    // via wppconnect.io/whatsapp-versions). A 20-month-old pin is
    // guaranteed to be rejected by WhatsApp's servers, which silently
    // breaks both fresh QR login and session restore. Since this repo
    // already tracks the latest whatsapp-web.js from GitHub main, the
    // library itself handles whatever version WhatsApp serves live —
    // no cache override needed. If a future WA update ever reintroduces
    // the old "reading 'r' of undefined" crash, re-pin to whatever
    // version is CURRENT at https://wppconnect.io/whatsapp-versions
    // at that time — never leave a static pin in place for months.
});

// Global watchdog: if neither 'qr' nor 'ready' fires at all (e.g. because
// WhatsApp's servers silently reject/hang the connection), the process
// used to hang until the GitHub Actions job timeout with zero signal.
// This forces a fast, loud failure so alert_failure.py actually runs today.
let initWatchdog = setTimeout(() => {
    console.error('Abort: Nem "qr" nem "ready" disparado em 90s. Provável incompatibilidade de versão do WhatsApp Web ou falha de rede.');
    client.destroy();
    process.exit(1);
}, 90000);

client.on('qr', (qr) => {
    clearTimeout(initWatchdog);
    if (qrTimeout) clearTimeout(qrTimeout); // don't stack timers if 'qr' auto-refreshes
    console.error('AVISO: Sessão expirou. Novo QR Code gerado.');
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

            let enviado = false;
            let ultimoErro = null;

            for (let tentativa = 1; tentativa <= 2 && !enviado; tentativa++) {
                try {
                    await client.sendMessage(groupId, mensagemLimpa);
                    enviado = true;
                    console.log(`Mensagem ${numero} enviada (tentativa ${tentativa}) — chamada resolvida sem erro.`);
                } catch (err) {
                    ultimoErro = err.message || String(err);
                    console.error(`Falha ao enviar mensagem ${numero} (tentativa ${tentativa}):`, ultimoErro);
                    if (tentativa < 2) {
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
