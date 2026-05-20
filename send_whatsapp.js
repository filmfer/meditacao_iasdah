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

// Função auxiliar de limpeza para correspondência de nomes em Comunidades
String.prototype.stripCustom = function() {
    return this.trim().toLowerCase().replace(/[\u200B-\u200D\uFEFF]/g, "");
};

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
        // --- ATUALIZADO: Força uma busca profunda em todos os chats ativos e arquivados ---
        const chats = await client.getChats();
        let targetChat = null;

        // O Nome exato do subgrupo da igreja como aparece dentro da Comunidade
        const nomeDoGrupoLido = "IASD Angra do Heroísmo"; 

        let groupId = process.env.WHATSAPP_GROUP_ID;
        if (groupId) {
            groupId = groupId.trim().replace(/['"]/g, '');
            if (groupId.includes('@g.us')) {
                console.log(`Tentando localizar por ID na Comunidade: ${groupId}`);
                targetChat = chats.find(chat => chat.id._serialized === groupId);
            }
        }

        // SE NÃO ENCONTRAR PELO ID, FAZEMOS A BUSCA DE COMUNIDADE POR NOME:
        if (!targetChat) {
            console.log(`ID não resolveu. Varrendo subgrupos da Comunidade por nome: "${nomeDoGrupoLido}"...`);
            
            // Varre todos os chats e remove espaços ocultos que o WhatsApp injeta em Comunidades
            targetChat = chats.find(chat => {
                return (chat.isGroup || chat.id._serialized.includes('@g.us')) && 
                       chat.name && 
                       chat.name.stripCustom() === nomeDoGrupoLido.stripCustom();
            });
        }

        // SE AINDA ASSIM NÃO ENCONTRAR (Comum em Comunidades novas no WhatsApp Web):
        if (!targetChat) {
            console.log('Tentando busca agressiva por histórico de Comunidade...');
            for (const chat of chats) {
                if (chat.name && chat.name.trim().toLowerCase() === nomeDoGrupoLido.trim().toLowerCase()) {
                    targetChat = chat;
                    break;
                }
            }
        }

        if (targetChat) {
            console.log(`Subgrupo da Comunidade localizado: "${targetChat.name}" (ID: ${targetChat.id._serialized})`);
            console.log('Iniciando transmissão do bloco de meditações...');
            
            await targetChat.sendMessage(message);
            
            console.log('Daily meditation cluster pushed successfully to WhatsApp Community group!');
            client.destroy();
            process.exit(0);
        } else {
            throw new Error('O subgrupo da Comunidade não foi localizado na lista de interações do WhatsApp Web.');
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
