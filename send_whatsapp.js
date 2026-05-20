const { Client, LocalAuth } = require('whatsapp-web.js');
const fs = require('fs');

const client = new Client({
    authStrategy: new LocalAuth({
        // 1. CORREÇÃO DA PASTA: Removemos o ponto inicial para deixar de ser oculta
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
});

client.on('qr', (qr) => {
    console.error('AVISO DE INFRAESTRUTURA: Nenhuma sessão ativa encontrada ou a sessão expirou.');
    require('qrcode-terminal').generate(qr, { small: true, inverse: true });
    setTimeout(() => { client.destroy(); process.exit(1); }, 90000);
});

client.on('ready', async () => {
    console.log('WhatsApp Client connection established successfully!');
    await new Promise(resolve => setTimeout(resolve, 5000));
    
    if (!fs.existsSync('whatsapp_msg.txt')) {
        console.error('Abort: whatsapp_msg.txt not found.');
        client.destroy();
        process.exit(1);
    }

    let message = fs.readFileSync('whatsapp_msg.txt', 'utf8');
    message = message.trim().replace(/\n\n={30}\n\n$/, '').trim();

    let groupId = process.env.WHATSAPP_GROUP_ID;
    if (!groupId) {
        console.error('Abort: WHATSAPP_GROUP_ID is missing.');
        client.destroy();
        process.exit(1);
    }
    groupId = groupId.trim().replace(/['"]/g, ''); 

    try {
        console.log(`Attempting to transmit message to group ID: ${groupId}`);
        
        const chat = await client.getChatById(groupId);
        await chat.sendMessage(message);
        
        console.log('Ordem de envio dada ao WhatsApp!');
        
        // 2. CORREÇÃO DE REDE: Esperar 8 segundos obrigatórios antes de fechar o programa
        // Isto garante que o payload viaja fisicamente até aos servidores da Meta
        console.log('A aguardar sincronização de rede...');
        await new Promise(resolve => setTimeout(resolve, 8000));
        
        console.log('Sincronização concluída. A encerrar com sucesso.');
        client.destroy();
        process.exit(0); 
    } catch (err) {
        console.error('Failed to transmit:', err.message || err);
        client.destroy();
        process.exit(1); 
    }
});

client.on('auth_failure', (msg) => {
    console.error('Authentication signature rejected:', msg);
    process.exit(1);
});

client.initialize();
