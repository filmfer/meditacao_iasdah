const { Client, LocalAuth } = require('whatsapp-web.js');
const fs = require('fs');

const client = new Client({
    authStrategy: new LocalAuth({
        dataPath: './.wwebjs_auth'
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
    console.error('CRITICAL ERROR: WhatsApp session has expired or was disconnected!');
    require('qrcode-terminal').generate(qr, { small: true, inverse: true });
    setTimeout(() => { client.destroy(); process.exit(1); }, 60000);
});

client.on('ready', async () => {
    console.log('WhatsApp Client connection established successfully!');
    console.log('Waiting 20 seconds for the interface to stabilize...');
    await new Promise(resolve => setTimeout(resolve, 20000));
    
    if (!fs.existsSync('whatsapp_msg.txt')) {
        console.error('Abort: whatsapp_msg.txt not found.');
        client.destroy();
        process.exit(1);
    }

    // --- CORREÇÃO 1: Limpeza profunda de espaços e quebras de linha fantasmas ---
    let message = fs.readFileSync('whatsapp_msg.txt', 'utf8');
    message = message.trim().replace(/\n\n={30}\n\n$/, '').trim();

    if (!message) {
        console.error('Abort: Message payload is empty after cleaning.');
        client.destroy();
        process.exit(1);
    }

    // --- CORREÇÃO 2: Limpeza rigorosa do ID do Grupo ---
    let groupId = process.env.WHATSAPP_GROUP_ID;
    if (!groupId) {
        console.error('Abort: WHATSAPP_GROUP_ID environment variable is missing.');
        client.destroy();
        process.exit(1);
    }
    groupId = groupId.trim().replace(/['"]/g, ''); // Remove aspas acidentais se existirem

    try {
        console.log(`Attempting to transmit message to verified group: ${groupId}`);
        
        // Em vez de enviar diretamente para uma string, validamos o formato do Chat ID
        const chat = await client.getChatById(groupId);
        await chat.sendMessage(message);
        
        console.log('Daily meditation cluster pushed successfully to WhatsApp!');
        client.destroy();
        process.exit(0); 
    } catch (err) {
        console.error('Failed to transmit message payload over WhatsApp Web interface:', err.message || err);
        client.destroy();
        process.exit(1); 
    }
});

client.on('auth_failure', (msg) => {
    console.error('Authentication signature rejected:', msg);
    process.exit(1);
});

client.initialize();
