const { Client, LocalAuth } = require('whatsapp-web.js');

const client = new Client({
    authStrategy: new LocalAuth({ dataPath: './.wwebjs_auth' }),
    puppeteer: {
        headless: true,
        args: [
            '--no-sandbox', '--disable-setuid-sandbox',
            '--disable-dev-shm-usage', '--disable-accelerated-2d-canvas',
            '--no-first-run', '--no-zygote', '--disable-gpu'
        ]
    }
});

client.on('qr', (qr) => {
    console.error('Sessão expirou no arranque de diagnóstico.');
    require('qrcode-terminal').generate(qr, { small: true, inverse: true });
    setTimeout(() => { client.destroy(); process.exit(1); }, 60000);
});

// --- MODO DETETIVE: LISTAR OS IDS DOS TEUS GRUPOS ---
client.on('ready', async () => {
    console.log('WhatsApp Client conectado com sucesso para diagnóstico!');
    
    try {
        const chats = await client.getChats();
        // Filtra apenas o que são grupos reais
        const grupos = chats.filter(chat => chat.isGroup);
        
        console.log("\n==================================================");
        console.log("🚨 LISTA DE GRUPOS ENCONTRADOS NO TEU WHATSAPP 🚨");
        console.log("==================================================");
        
        grupos.forEach(g => {
            console.log(`NOME DO GRUPO: ${g.name}`);
            console.log(`👉 ID PARA COPIAR: ${g.id._serialized}`);
            console.log("--------------------------------------------------");
        });
        
        console.log("==================================================\n");
        
        client.destroy();
        process.exit(0); // Fecha com sucesso após listar
    } catch (err) {
        console.error('Erro ao listar grupos:', err.message);
        client.destroy();
        process.exit(1);
    }
});

client.initialize();
