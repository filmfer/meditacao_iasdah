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
});

client.on('qr', (qr) => {
    console.error('AVISO: Sessão expirou. Novo QR Code gerado.');
    require('qrcode-terminal').generate(qr, { small: true, inverse: true });
    setTimeout(() => { client.destroy(); process.exit(1); }, 90000);
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

    // Lê o arquivo gerado pelo Python
    const rawContent = fs.readFileSync('whatsapp_msg.txt', 'utf8');
    
    // --- NOVO: Divide o texto em mensagens individuais através do separador ---
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
        console.log(`Grupo de Comunidade alvo: ${groupId}`);
        const chat = await client.getChatById(groupId);
        
        // --- MOTOR DE ENVIO INDIVIDUAL COM COMPASSO DE ESPERA ---
        for (let i = 0; i < mensagens.length; i++) {
            console.log(`\nA processar publicação ${i + 1} de ${mensagens.length}...`);
            
            // Envia a mensagem individual
            await chat.sendMessage(mensagens[i]);
            console.log(`Mensagem ${i + 1} colada no chat.`);
            
            // Se não for a última mensagem, aguarda 10 segundos para carregar o Thumbnail
            // antes de enviar a meditação seguinte.
            if (i < mensagens.length - 1) {
                console.log('⏱️ Aguarda 10 segundos para carregar o thumbnail do link do YouTube...');
                await new Promise(resolve => setTimeout(resolve, 10000));
            }
        }
        
        // Sincronização final de rede para garantir o escoamento total das 3 mensagens
        console.log('\nA aguardar sincronização final de rede (8 segundos)...');
        await new Promise(resolve => setTimeout(resolve, 8000));
        
        console.log('Todas as meditações foram publicadas individualmente com sucesso!');
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
