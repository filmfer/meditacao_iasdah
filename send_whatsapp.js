const { Client, LocalAuth } = require('whatsapp-web.js');
const fs = require('fs');

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
    // Add this webVersionCache block:
    webVersionCache: {
        type: 'remote',
        remotePath: 'https://raw.githubusercontent.com/wppconnect-team/wa-version/main/html/2.2412.54.html'
    }
});

client.on('qr', (qr) => {
    console.error('AVISO: Sessão expirou. Novo QR Code gerado.');
    require('qrcode-terminal').generate(qr, { small: true, inverse: true });
    setTimeout(() => { client.destroy(); process.exit(1); }, 60000);
});

client.on('ready', async () => {
    console.log('WhatsApp Client connection established successfully!');
    console.log('A aguardar 5 segundos para estabilização inicial...');
    await new Promise(resolve => setTimeout(resolve, 5000));
    
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
        const chat = await client.getChatById(groupId);
        
        for (let i = 0; i < mensagens.length; i++) {
            console.log(`\nA processar publicação ${i + 1} de ${mensagens.length}...`);
            
            // --- CORREÇÃO DO MARKDOWN: Limpa as barras de escape (\) que o WhatsApp não usa ---
            // Remove as barras antes de pontos, traços, parêntesis e chavetas
            let mensagemLimpa = mensagens[i].replace(/\\([.\-_()!\[\]])/g, '$1');
            
            // Correção extra para links URL que possam ter ficado com escapes ocultos
            mensagemLimpa = mensagemLimpa.replace(/\\_/g, '_').replace(/\\=/g, '=');

            // Envia a mensagem limpa
            await chat.sendMessage(mensagemLimpa);
            console.log(`Mensagem ${i + 1} colada no chat (Markdown limpo).`);
            
            if (i < mensagens.length - 1) {
                console.log('⏱️ Aguarda 10 segundos para carregar o thumbnail do link do YouTube...');
                await new Promise(resolve => setTimeout(resolve, 10000));
            }
        }
        
        console.log('\nA aguardar sincronização final de rede (8 segundos)...');
        await new Promise(resolve => setTimeout(resolve, 8000));
        
        console.log('Todas as meditações foram publicadas de forma limpa e individual!');
        client.destroy();
        process.exit(0); 
    } catch (err) {
        console.error('Erro durante o envio individual:', err.message || err);
        client.destroy();
        process.exit(1); 
    }
});

client.on('auth_failure', (msg) => {
    console.error('Falha na assinatura de autenticação:', msg);
    process.exit(1);
});

client.initialize();
