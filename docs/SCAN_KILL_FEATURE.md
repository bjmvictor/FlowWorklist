# Funcionalidade: Scan & Kill (Limpar Processos Órfãos)

## Descrição

A funcionalidade **Scan & Kill** (Limpar Processos Órfãos) foi adicionada para resolver um problema comum: quando o serviço DICOM MWL relata que iniciou, mas a interface web mostra "Parado", ou vice-versa. Isto ocorre quando há processos órfãos do `mwl_service.py` ainda em execução.

## Localização na Interface

O botão **"Limpar processos órfãos"** está discretamente integrado no **Card de Status do Serviço**, no canto superior direito:

```
┌─ Status do Serviço ──────────────────────────┐
│ ✓ Em execução                    [Limpar]   │
│ PID: 24752                       [ícone]   │
└──────────────────────────────────────────────┘
```

O botão é pequeno e discreto, com baixa opacidade, indicando que é uma função de suporte/troubleshooting.

## Como Funciona

### Antes (Problema)
1. Serviço diz que iniciou, mas status mostra "Parado"
2. Tentar iniciar novamente retorna erro "já em execução"
3. Impossível saber qual processo realmente está rodando

### Depois (Solução)
1. Clique em "Limpar processos órfãos"
2. O sistema:
   - Escaneia todos os processos `mwl_service.py` em execução (via PowerShell CIM ou ps/grep)
   - Mata todos os encontrados
   - Remove os arquivos `service.pid` e `mwl_server.lock`
3. Clique em "Iniciar" para começar limpo

## Implementação Técnica

### Backend (Python - `flow.py`)

#### Novas Funções

```python
find_service_pids() -> list[int]
```
Descobre todos os PIDs de serviço em execução:
- Windows: usa PowerShell CIM (com fallback para WMIC)
- Linux/macOS: usa `ps grep`

```python
kill_orphan_services() -> dict
```
Mata todos os processos órfãos:
- Retorna: `{'ok': True/False, 'killed': [pid1, pid2, ...], 'errors': [...]}`

### Rota Flask (em `webui/app.py`)

```python
POST /service/scan-kill
```
Endpoint que invoca `kill_orphan_services()` e retorna JSON com resultado.

### Frontend (JavaScript/HTML)

- Botão integrado ao Status Card (baixa opacidade)
- Função `scanAndKill()` que:
  1. Mostra notificação "Verificando..."
  2. Chama `POST /service/scan-kill`
  3. Mostra resultado (quantos PIDs foram eliminados)
  4. Recarrega a página após 1.2s

## Traduções Disponíveis

Todas as 10 idiomas suportados receberam as novas strings:

| Idioma | Texto do Botão | Tooltip |
|--------|---|---|
| PT 🇧🇷 | Limpar processos órfãos | Localizar e eliminar processos de serviço em execução |
| EN 🇺🇸 | Clear orphan processes | Locate and kill running service processes |
| FR 🇫🇷 | Effacer les processus orphelins | Localiser et arrêter les processus de service |
| ES 🇪🇸 | Limpiar procesos huérfanos | Localizar y eliminar procesos de servicio |
| ZH 🇨🇳 | 清除孤立进程 | 查找并结束运行中的服务进程 |
| RU 🇷🇺 | Очистить потерянные процессы | Найти и завершить выполняемые процессы |
| JA 🇯🇵 | 孤立プロセスを削除 | 実行中のサービスプロセスを探して終了する |
| IT 🇮🇹 | Cancella processi orfani | Localizza e termina i processi di servizio |
| TR 🇹🇷 | Yetim işlemleri temizle | Çalışan hizmet işlemlerini bulun |
| FIL 🇵🇭 | Burahin ang orphan processes | Hanapin at aksyunan ang tumatakbong services |

## Testes

Todos os cenários foram testados:

✓ `find_service_pids()` - encontra múltiplos PIDs em execução  
✓ `kill_orphan_services()` - mata com sucesso e limpa arquivos  
✓ Estrutura de resposta `/status` - alinhada e sem KeyErrors  
✓ Teste de status (`/test/status`) - sem erros de KeyError  
✓ Limpeza de arquivos - `service.pid` e `mwl_server.lock` removidos  

## Uso por CLI (Opcional)

Se preferir, também pode executar via linha de comando:

```powershell
# Encontrar PIDs
python -c "import flow; print(flow.find_service_pids())"

# Matar tudo
python -c "import flow; print(flow.kill_orphan_services())"

# Ou via flow.py
flow status
```

## Notas Importantes

1. **Apenas use em caso de problemas** - o botão está discreto por isso
2. **O endpoint limpa proativamente** - não verifica antes de matar (seguro para recuperação)
3. **Sem risco de falsos positivos** - processa apenas `mwl_service.py`, não outros serviços
4. **Windows/Linux compatível** - implementação automática por SO

## Exemplo de Fluxo

```
1. Aplicação mostra "Parado" mas serviço está meio-vivo
   ↓
2. Clique em "Limpar processos órfãos"
   ↓
3. Sistema encontra PIDs: [13652, 24244] e mata ambos
   ↓
4. Notificação: "Eliminados 2 processo(s): 13652, 24244"
   ↓
5. Página recarrega automaticamente
   ↓
6. Agora pode iniciar limpo com "Iniciar"
```

## Resolução de Problemas

### Botão não aparece
- Limpe o cache do navegador (Ctrl+Shift+R)
- Reinicie a aplicação web: `flow stopapp && flow startapp`

### Processo não foi eliminado
- Pode ser que não haja processos órfãos em execução
- Verifique logs: `flow logs`

### Erro ao eliminar
- Verifique permissões (pode ser necessário admin em Windows)
- Procure por arquivos bloqueados em `service_logs/`
