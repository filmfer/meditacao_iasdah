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
}); // Note: webVersionCache has been removed so the patched library can do its job.

let qrTimeout;

client.on('qr', (qr) => {
    console.error('AVISO: Sessão expirou. Novo QR Code gerado.');
    require('qrcode-terminal').generate(qr, { small: true, inverse: true });
    
    // 2. Assign the timer to the variable and increase the wait time to 90 seconds just in case
    qrTimeout = setTimeout(() => { 
        console.error('Abort: QR Code não foi lido a tempo.');
        client.destroy(); 
        process.exit(1); 
    }, 90000);
});

client.on('ready', async () => {
    // 3. Cancel the self-destruct timer the moment the client connects
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
        const chat = await client.getChatById(groupId);
        
        // --- VERIFICAÇÃO DE SEGURANÇA ---
        if (!chat) {
            console.error('Erro Crítico: O grupo não foi encontrado. A sincronização de chats pode não ter terminado.');
            client.destroy();
            process.exit(1);
        }
        
        for (let i = 0; i < mensagens.length; i++) {
            console.log(`\nA processar publicação ${i + 1} de ${mensagens.length}...`);
            
            // --- CORREÇÃO DO MARKDOWN ---
            let mensagemLimpa = mensagens[i].replace(/\\([.\-_()!\[\]])/g, '$1');
            mensagemLimpa = mensagemLimpa.replace(/\\_/g, '_').replace(/\\=/g, '=');

            await chat.sendMessage(mensagemLimpa);
            console.log(`Mensagem ${i + 1} colada no chat (Markdown limpo).`);
            
            if (i < mensagens.length - 1) {
                console.log('⏱️ Aguarda 10 segundos para carregar o thumbnail do link do YouTube...');
                await new Promise(resolve => setTimeout(resolve, 10000));
            }
        }
        
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
