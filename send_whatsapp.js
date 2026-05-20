const { Client, LocalAuth } = require('whatsapp-web.js');
const fs = require('fs');

// Inicializa o cliente apontando para a diretoria persistente carregada via Artifacts
const client = new Client({
    authStrategy: new LocalAuth({
        dataPath: './.wwebjs_auth'
    }),
    puppeteer: {
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }
});

// Captura se a sessão caiu. Se cair, força o encerramento com erro para disparar o pipeline de alerta
client.on('qr', (qr) => {
    console.error('CRITICAL ERROR: WhatsApp session has expired or was disconnected!');
    console.log('A new QR code session initialization is required.');
    
    // Mostra o QR code terminal apenas caso queira debugar manualmente nos logs
    require('qrcode-terminal').generate(qr, { small: true });
    
    client.destroy();
    process.exit(1); 
});

client.on('ready', async () => {
    console.log('WhatsApp Client connection established successfully!');
    
    if (!fs.existsSync('whatsapp_msg.txt')) {
        console.error('Abort: whatsapp_msg.txt output payload not found.');
        client.destroy();
        process.exit(1);
    }

    let message = fs.readFileSync('whatsapp_msg.txt', 'utf8');
    
    // Remove o separador decorativo final para o envio ficar limpo
    message = message.trim().replace(/\n\n={30}\n\n$/, '');

    const groupId = process.env.WA_GROUP_ID;
    if (!groupId) {
        console.error('Abort: WA_GROUP_ID environment variable is missing.');
        client.destroy();
        process.exit(1);
    }

    try {
        await client.sendMessage(groupId, message);
        console.log('Daily meditation cluster pushed successfully to WhatsApp!');
        client.destroy();
        process.exit(0); 
    } catch (err) {
        console.error('Failed to transmit message payload over WhatsApp Web interface:', err);
        client.destroy();
        process.exit(1); 
    }
});

client.on('auth_failure', (msg) => {
    console.error('Authentication signature rejected:', msg);
    process.exit(1);
});

client.initialize();
