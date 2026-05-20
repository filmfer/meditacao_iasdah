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

// Se por algum motivo a sessão cair no futuro, ele avisa e gera o QR
client.on('qr', (qr) => {
    console.error('CRITICAL ERROR: WhatsApp session has expired or was disconnected!');
    require('qrcode-terminal').generate(qr, { small: true, inverse: true });
    setTimeout(() => { client.destroy(); process.exit(1); }, 60000);
});

client.on('ready', async () => {
    console.log('WhatsApp Client connection established successfully!');
    console.log('Waiting 5 seconds for the interface to stabilize...');
    await new Promise(resolve => setTimeout(resolve, 5000));
    
    if (!fs.existsSync('whatsapp_msg.txt')) {
        console.error('Abort: whatsapp_msg.txt not found.');
        client.destroy();
        process.exit(1);
    }

    let message = fs.readFileSync('whatsapp_msg.txt', 'utf8');
    message = message.trim().replace(/\n\n={30}\n\n$/, '').trim();

    if (!message) {
        console.error('Abort: Message payload is empty.');
        client.destroy();
        process.exit(1);
    }

    try {
        const chats = await client.getChats();
        let targetChat = null;

        // TENTATIVA 1: Procurar pelo ID guardado nos Secrets
        let groupId = process.env.WHATSAPP_GROUP_ID;
        if (groupId) {
            groupId = groupId.trim().replace(/['"]/g, '');
            if (groupId.includes('@g.us')) {
                console.log(`Attempting to find group by ID: ${groupId}`);
                targetChat = chats.find(chat => chat.id._serialized === groupId);
            }
        }

        // TENTATIVA 2: Se o ID não funcionar ou for o link, procuramos pelo NOME real do grupo!
        if (!targetChat) {
            console.log('Group ID not valid or not found. Searching all chats for the Church Group...');
            
            // INDICA O NOME DO TEU GRUPO: O script varre o teu WhatsApp à procura do nome correto
            // Se o teu grupo não se chamar exatamente "Meditações IASD", altera o texto abaixo entre aspas:
            const nomeDoGrupoLido = "Meditações IASD"; 
            
            targetChat = chats.find(chat => chat.isGroup && chat.name.trim() === nomeDoGrupoLido.trim());
        }

        if (targetChat) {
            console.log(`Group found: "${targetChat.name}" (ID: ${targetChat.id._serialized})`);
            console.log('Transmitting daily meditation cluster...');
            
            await targetChat.sendMessage(message);
            
            console.log('Daily meditation cluster pushed successfully to WhatsApp!');
            client.destroy();
            process.exit(0);
        } else {
            throw new Error('Church group chat could not be located in the active chat list.');
        }

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
