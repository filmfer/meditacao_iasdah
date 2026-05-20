const { Client, LocalAuth } = require('whatsapp-web.js');
const fs = require('fs');

// Inicializa o cliente com argumentos estáveis para o ambiente Linux do GitHub Actions
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

// Intercetador de segurança: Se a sessão cair no futuro, gera o QR Code e avisa o Telegram
client.on('qr', (qr) => {
    console.error('AVISO DE INFRAESTRUTURA: Nenhuma sessão ativa encontrada ou a sessão expirou.');
    console.log('A gerar novo QR Code obrigatório. Por favor escaneia no ecrã abaixo:');
    
    // Força a impressão correta com cores invertidas
    require('qrcode-terminal').generate(qr, { small: true, inverse: true });
    
    // Deixa o ecrã congelado por 90 segundos para te dar tempo de escanear antes de avançar
    setTimeout(() => {
        console.log('Tempo limite de scan atingido.');
        client.destroy();
        process.exit(1); 
    }, 90000);
});

// Execução principal quando o cliente está autenticado e pronto
client.on('ready', async () => {
    console.log('WhatsApp Client connection established successfully!');
    console.log('Waiting 20 seconds for the interface to stabilize...');
    
    // Pausa de segurança crucial para mitigar ecrãs de boas-vindas da Meta
    await new Promise(resolve => setTimeout(resolve, 20000));
    
    // Valida a existência do payload de texto gerado pelo Python
    if (!fs.existsSync('whatsapp_msg.txt')) {
        console.error('Abort: whatsapp_msg.txt output payload not found.');
        client.destroy();
        process.exit(1);
    }

    // Lê e limpa o texto das meditações
    let message = fs.readFileSync('whatsapp_msg.txt', 'utf8');
    message = message.trim().replace(/\n\n={30}\n\n$/, '').trim();

    if (!message) {
        console.error('Abort: Message payload is empty after cleaning.');
        client.destroy();
        process.exit(1);
    }

    // Carrega o Chat ID guardado nos teus Secrets do GitHub
    let groupId = process.env.WHATSAPP_GROUP_ID;
    if (!groupId) {
        console.error('Abort: WHATSAPP_GROUP_ID environment variable is missing.');
        client.destroy();
        process.exit(1);
    }
    
    // Limpeza rigorosa contra aspas acidentais no segredo
    groupId = groupId.trim().replace(/['"]/g, ''); 

    try {
        console.log(`Attempting to transmit message to verified group ID: ${groupId}`);
        
        // Abre e valida o ID do chat diretamente na infraestrutura da Comunidade
        const chat = await client.getChatById(groupId);
        await chat.sendMessage(message);
        
        console.log('Daily meditation cluster pushed successfully to WhatsApp Community group!');
        client.destroy();
        process.exit(0); // Código de sucesso total
    } catch (err) {
        console.error('Failed to transmit message payload over WhatsApp Web interface:', err.message || err);
        client.destroy();
        process.exit(1); // Força falha para ativar o alarme no Telegram pessoal
    }
});

// Trata rejeição de chaves criptográficas
client.on('auth_failure', (msg) => {
    console.error('Authentication signature rejected:', msg);
    process.exit(1);
});

client.initialize();
