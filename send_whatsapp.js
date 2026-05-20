try {
        // --- ATUALIZADO: Força uma busca profunda em todos os chats ativos e arquivados ---
        const chats = await client.getChats();
        let targetChat = null;

        // O Nome exato do subgrupo da igreja como aparece dentro da Comunidade
        const nomeDoGrupoLido = "Meditações IASD"; 

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
