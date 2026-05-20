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
    console.log('A new QR code session initialization is required.');
    
    require('qrcode-terminal').generate(qr, { small: true, inverse: true });
    
    setTimeout(() => {
        client.destroy();
        process.exit(1); 
    }, 60000);
});

// --- ATUALIZADO: Adicionada tolerância para o primeiro arranque ---
client.on('ready', async () => {
    console.log('WhatsApp Client connection established successfully!');
    console.log('Waiting 5 seconds for the interface to stabilize...');
    
    // Pequena pausa de segurança para fechar pop-ups iniciais do WhatsApp
    await new Promise(resolve => setTimeout(resolve, 20000));
    
    if (!fs.existsSync('whatsapp_msg.txt')) {
        console.error('Abort: whatsapp_msg.txt output payload not found.');
        client.destroy();
        process.exit(1);
    }

    let message = fs.readFileSync('whatsapp_msg.txt', 'utf8');
    message = message.trim().replace(/\n\n={30}\n\n$/, '');

    const groupId = process.env.WHATSAPP_GROUP_ID;
    if (!groupId) {
        console.error('Abort: WHATSAPP_GROUP_ID environment variable is missing.');
        client.destroy();
        process.exit(1);
    }

    try {
        console.log(`Attempting to transmit message to group: ${groupId}`);
        await client.sendMessage(groupId, message);
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
