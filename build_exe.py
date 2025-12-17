"""
FlowWorklist - Build Script for Windows Executable
Creates a standalone .exe file for easy deployment
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

# Configurar encoding para Unicode no Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

ROOT = Path(__file__).parent.resolve()

def check_pyinstaller():
    """Verifica se PyInstaller está instalado"""
    try:
        import PyInstaller
        print("[OK] PyInstaller {} encontrado".format(PyInstaller.__version__))
        return True
    except ImportError:
        print("[ERRO] PyInstaller nao encontrado")
        print("\nInstalando PyInstaller...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("[OK] PyInstaller instalado com sucesso")
            return True
        except subprocess.CalledProcessError:
            print("[ERRO] Falha ao instalar PyInstaller")
            return False

def build_executable():
    """Gera o executável do FlowWorklist"""
    print("\n" + "="*60)
    print("FlowWorklist - Build Executavel Windows")
    print("="*60 + "\n")
    
    if not check_pyinstaller():
        return False
    
    # Preparar diretórios
    dist_dir = ROOT / "dist"
    build_dir = ROOT / "build"
    spec_file = ROOT / "FlowWorklist.spec"
    
    # Limpar builds anteriores
    if dist_dir.exists():
        print("Limpando dist/...")
        shutil.rmtree(dist_dir)
    if build_dir.exists():
        print("Limpando build/...")
        shutil.rmtree(build_dir)
    if spec_file.exists():
        print("Removendo FlowWorklist.spec...")
        spec_file.unlink()
    
    print("\n[PROCESSANDO] Gerando executavel...")
    print("Isso pode levar alguns minutos...\n")
    
    # Comando PyInstaller (versão otimizada sem collect-all que causa problemas)
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=FlowWorklist",
        "--onefile",  # Gera um único .exe
        "--console",  # Mantém console para troubleshooting
        "--add-data={}{}webui".format("webui", os.pathsep),  # Inclui templates e static
        "--add-data={}{}." .format("config.json", os.pathsep),  # Inclui config padrão
        "--hidden-import=flask",
        "--hidden-import=pydicom",
        "--hidden-import=pynetdicom",
        "--hidden-import=oracledb",
        "--hidden-import=pymysql",
        "--hidden-import=unidecode",
        "--hidden-import=blinker",
        "--hidden-import=werkzeug",
        "--hidden-import=jinja2",
        "--hidden-import=click",
        "--collect-all=flask",
        "--noupx",  # Desabilita UPX que pode causar problemas
        "--noconfirm",  # Não pede confirmação
        "--clean",  # Limpa arquivos temporários
        "startapp.py"
    ]
    
    # Remover argumentos vazios
    cmd = [arg for arg in cmd if arg]
    
    try:
        subprocess.check_call(cmd)
        
        print("\n" + "="*60)
        print("[OK] BUILD CONCLUIDO COM SUCESSO!")
        print("="*60)
        
        exe_path = dist_dir / "FlowWorklist.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print("\n[ARQUIVO] Executavel gerado: {}".format(exe_path))
            print("[TAMANHO] {:.1f} MB".format(size_mb))
            print("\n[INSTRUCOES] COMO USAR:")
            print("   1. Copie FlowWorklist.exe para o servidor")
            print("   2. Copie config.json e edite com suas credenciais")
            print("   3. Execute FlowWorklist.exe")
            print("   4. Acesse http://localhost:5000")
            print("\n[DICA] Use NSSM para instalar como servico Windows")
            print('   nssm install FlowWorklist "C:\\Path\\To\\FlowWorklist.exe"')
            return True
        else:
            print("\n[ERRO] Executavel nao foi gerado")
            return False
            
    except subprocess.CalledProcessError as e:
        print("\n[ERRO] ERRO durante build: {}".format(e))
        print("\n[DICA] Tente o build do servico apenas:")
        print("   python build_exe.py")
        print("   Opcao 2: Apenas Servico DICOM (CLI)")
        return False
    except Exception as e:
        print("\n[ERRO] ERRO inesperado: {}".format(e))
        return False

def build_service_only():
    """Gera executável apenas do serviço DICOM (sem UI)"""
    print("\n" + "="*60)
    print("FlowWorklist - Build Servico DICOM (CLI)")
    print("="*60 + "\n")
    
    if not check_pyinstaller():
        return False
    
    dist_dir = ROOT / "dist"
    
    print("\n[PROCESSANDO] Gerando executavel do servico...")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=FlowWorklist-Service",
        "--onefile",
        "--console",  # Mantém console para logs
        "--add-data={}{}." .format("config.json", os.pathsep),
        "--hidden-import=pydicom",
        "--hidden-import=pynetdicom",
        "--hidden-import=oracledb",
        "--hidden-import=pymysql",
        "--hidden-import=unidecode",
        "--noupx",
        "--noconfirm",
        "--clean",
        "mwl_service.py"
    ]
    
    cmd = [arg for arg in cmd if arg]
    
    try:
        subprocess.check_call(cmd)
        
        print("\n[OK] Servico DICOM gerado com sucesso!")
        exe_path = dist_dir / "FlowWorklist-Service.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print("[ARQUIVO] {}".format(exe_path))
            print("[TAMANHO] {:.1f} MB".format(size_mb))
            print("\n[INSTRUCOES] Execute: FlowWorklist-Service.exe")
            print("   Ou instale como servico: nssm install FlowMWL FlowWorklist-Service.exe")
            return True
            
    except subprocess.CalledProcessError as e:
        print("[ERRO] Erro durante build: {}".format(e))
        return False
    except Exception as e:
        print("[ERRO] Erro inesperado: {}".format(e))
        return False

if __name__ == "__main__":
    print("\nEscolha o tipo de build:")
    print("1. Completo (Dashboard + Servico DICOM)")
    print("2. Apenas Servico DICOM (CLI)")
    print("3. Ambos")
    
    choice = input("\nOpcao [1-3]: ").strip()
    
    success = True
    
    if choice == "1":
        success = build_executable()
    elif choice == "2":
        success = build_service_only()
    elif choice == "3":
        success = build_executable() and build_service_only()
    else:
        print("Opcao invalida")
        success = False
    
    if not success:
        sys.exit(1)
    
    print("\n[OK] Processo concluido!")
    input("\nPressione ENTER para sair...")
