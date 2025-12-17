# FlowWorklist - Guia de Build Executável Windows

Este guia explica como criar um executável standalone (.exe) do FlowWorklist para facilitar a implantação em ambientes Windows sem necessidade de Python instalado.

## 📋 Pré-requisitos

- Python 3.8 ou superior instalado
- Virtual environment configurado e ativado
- Dependências do projeto instaladas (`pip install -r requirements.txt`)

## 🚀 Processo de Build

### Opção 1: Build Automático (Recomendado)

```powershell
# Execute o script de build
python build_exe.py
```

O script apresentará as seguintes opções:

1. **Completo** - Dashboard + Serviço DICOM (FlowWorklist.exe)
2. **Apenas Serviço DICOM** - CLI apenas (FlowWorklist-Service.exe)
3. **Ambos** - Gera os dois executáveis

### Opção 2: Build Manual

#### Build Completo (Dashboard + DICOM)

```powershell
# Instalar PyInstaller
pip install pyinstaller

# Gerar executável
pyinstaller --name=FlowWorklist `
  --onefile `
  --windowed `
  --add-data="webui;webui" `
  --add-data="config.json;." `
  --hidden-import=pynetdicom `
  --hidden-import=pydicom `
  --hidden-import=flask `
  --hidden-import=oracledb `
  --hidden-import=pymysql `
  --collect-all=pynetdicom `
  --collect-all=pydicom `
  --collect-all=flask `
  startapp.py
```

#### Build Serviço DICOM (CLI)

```powershell
pyinstaller --name=FlowWorklist-Service `
  --onefile `
  --console `
  --add-data="config.json;." `
  --hidden-import=pynetdicom `
  --hidden-import=pydicom `
  --hidden-import=oracledb `
  --hidden-import=pymysql `
  --collect-all=pynetdicom `
  --collect-all=pydicom `
  mwl_service.py
```

## 📦 Arquivos Gerados

Após o build, você encontrará:

```
FlowWorklist/
├── dist/
│   ├── FlowWorklist.exe          # Executável completo (~80-120 MB)
│   └── FlowWorklist-Service.exe  # Serviço DICOM apenas (~60-80 MB)
├── build/                         # Arquivos temporários (pode deletar)
└── FlowWorklist.spec             # Configuração PyInstaller (pode deletar)
```

## 🔧 Implantação do Executável

### Passo 1: Preparar Arquivos

Copie para o servidor de produção:

```
C:\FlowWorklist\
├── FlowWorklist.exe        # Executável principal
├── config.json             # Configuração (EDITE com credenciais reais!)
└── logs\                   # Pasta de logs (será criada automaticamente)
```

### Passo 2: Configurar config.json

**⚠️ IMPORTANTE**: O `config.json` incluído no executável contém dados de teste. Você DEVE criar um `config.json` real:

```json
{
  "server": {
    "aet": "FlowMWL",
    "port": 11112,
    "host": "0.0.0.0"
  },
  "database": {
    "type": "oracle",
    "user": "SEU_USUARIO",
    "password": "SUA_SENHA",
    "dsn": "IP:PORTA/SID",
    "query": "SELECT ... (sua query com 17 colunas)"
  },
  "ui": {
    "language": "pt"
  }
}
```

### Passo 3: Executar

#### Modo Manual

```powershell
# Execute diretamente
.\FlowWorklist.exe

# Acesse o dashboard
Start-Process "http://localhost:5000"
```

#### Modo Serviço (Recomendado)

##### Usando NSSM (Mais fácil)

```powershell
# Download NSSM: https://nssm.cc/download

# Instalar serviço
nssm install FlowWorklist "C:\FlowWorklist\FlowWorklist.exe"
nssm set FlowWorklist AppDirectory "C:\FlowWorklist"
nssm set FlowWorklist DisplayName "FlowWorklist DICOM MWL Server"
nssm set FlowWorklist Description "DICOM Modality Worklist Service with Web Dashboard"
nssm set FlowWorklist Start SERVICE_AUTO_START

# Configurar restart automático
nssm set FlowWorklist AppThrottle 1500
nssm set FlowWorklist AppExit Default Restart
nssm set FlowWorklist AppRestartDelay 5000

# Iniciar serviço
nssm start FlowWorklist

# Verificar status
nssm status FlowWorklist

# Gerenciar
nssm stop FlowWorklist
nssm restart FlowWorklist
nssm remove FlowWorklist confirm
```

##### Usando sc.exe (Nativo Windows)

```powershell
# Criar serviço
sc.exe create FlowWorklist binPath= "C:\FlowWorklist\FlowWorklist.exe" start= auto
sc.exe description FlowWorklist "DICOM Modality Worklist Service"

# Iniciar
sc.exe start FlowWorklist

# Gerenciar
sc.exe stop FlowWorklist
sc.exe delete FlowWorklist
```

## 🔍 Verificação

### Testar Dashboard

```powershell
# Abrir navegador
Start-Process "http://localhost:5000"
```

### Testar Porta DICOM

```powershell
# Verificar se porta 11112 está aberta
Test-NetConnection -ComputerName localhost -Port 11112
```

### Verificar Logs

```powershell
# Ver logs do serviço
Get-Content C:\FlowWorklist\logs\mwl_server.log -Tail 50 -Wait
```

## 📊 Comparação: Executável vs Python

| Aspecto | Executável (.exe) | Python |
|---------|-------------------|--------|
| **Tamanho** | 80-120 MB | ~5 MB |
| **Dependências** | Nenhuma (tudo incluído) | Python + pip packages |
| **Instalação** | Copiar e executar | Instalar Python + venv + deps |
| **Inicialização** | ~5-10 segundos | ~2-3 segundos |
| **Atualização** | Substituir .exe | `git pull` + `pip install` |
| **Portabilidade** | ✅ Executar em qualquer Windows | ❌ Requer Python instalado |
| **Tamanho no disco** | ~120 MB | ~220 MB (com venv) |

## ⚡ Otimizações

### Reduzir Tamanho do Executável

```powershell
# Use UPX para comprimir (reduz ~30-40%)
# Download: https://upx.github.io/

pyinstaller --onefile --upx-dir=C:\upx startapp.py
```

### Build Otimizado para Produção

```powershell
# Remover debug symbols e otimizar
pyinstaller --onefile `
  --optimize=2 `
  --strip `
  --clean `
  --noconfirm `
  startapp.py
```

## 🐛 Troubleshooting

### Erro: "Failed to execute script"

**Causa**: Falta de dependências ou módulos não encontrados.

**Solução**: Adicione os módulos faltantes:

```powershell
pyinstaller --onefile `
  --hidden-import=MODULO_FALTANTE `
  startapp.py
```

### Erro: "config.json not found"

**Causa**: O executável não encontra o arquivo de configuração.

**Solução**: Coloque `config.json` no mesmo diretório do .exe ou use caminho absoluto.

### Executável muito lento para iniciar

**Causa**: PyInstaller extrai arquivos temporários toda vez.

**Solução**: Use `--onedir` em vez de `--onefile` (gera pasta em vez de único .exe).

### Antivírus bloqueia o executável

**Causa**: Falso positivo comum com PyInstaller.

**Solução**: 
1. Adicione exceção no antivírus
2. Assine digitalmente o .exe
3. Use build `--onedir` que é menos suspeito

## 📝 Notas Importantes

1. **Segurança**: O `config.json` com credenciais deve ter permissões restritas
2. **Firewall**: Libere porta 11112 (DICOM) e 5000 (Dashboard)
3. **Atualizações**: Para atualizar, substitua apenas o .exe (config.json permanece)
4. **Logs**: Verifique regularmente os logs em `C:\FlowWorklist\logs\`
5. **Backup**: Faça backup do `config.json` antes de atualizações

## 🔗 Recursos Adicionais

- [PyInstaller Documentation](https://pyinstaller.org/en/stable/)
- [NSSM Documentation](https://nssm.cc/usage)
- [DEPLOYMENT.md](DEPLOYMENT.md) - Guia completo de implantação
- [README.md](README.md) - Documentação principal

## 📞 Suporte

Para problemas com o build ou executável:

1. Verifique logs em `logs/`
2. Execute com `--debug all` para mais informações
3. Consulte [GitHub Issues](https://github.com/bjmvictor/FlowWorklist/issues)

---

**Última atualização**: Dezembro 2025  
**Versão**: 1.0.0
