"""
FlowWorklist - Build Script for Windows Executable
Creates a standalone .exe file for easy deployment
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.resolve()

def check_pyinstaller():
    """Verifica se PyInstaller está instalado"""
    try:
        import PyInstaller
        print(f"✓ PyInstaller {PyInstaller.__version__} encontrado")
        return True
    except ImportError:
        print("✗ PyInstaller não encontrado")
        print("\nInstalando PyInstaller...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("✓ PyInstaller instalado com sucesso")
            return True
        except subprocess.CalledProcessError:
            print("✗ Falha ao instalar PyInstaller")
            return False

def build_executable():
    """Gera o executável do FlowWorklist"""
    print("\n" + "="*60)
    print("FlowWorklist - Build Executável Windows")
    print("="*60 + "\n")
    
    if not check_pyinstaller():
        return False
    
    # Preparar diretórios
    dist_dir = ROOT / "dist"
    build_dir = ROOT / "build"
    spec_file = ROOT / "FlowWorklist.spec"
    
    # Limpar builds anteriores
    if dist_dir.exists():
        print(f"Limpando {dist_dir}...")
        shutil.rmtree(dist_dir)
    if build_dir.exists():
        print(f"Limpando {build_dir}...")
        shutil.rmtree(build_dir)
    if spec_file.exists():
        print(f"Removendo {spec_file}...")
        spec_file.unlink()
    
    print("\n📦 Gerando executável...")
    print("Isso pode levar alguns minutos...\n")
    
    # Comando PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=FlowWorklist",
        "--onefile",  # Gera um único .exe
        "--windowed",  # Sem console (apenas GUI)
        "--icon=webui/static/brand/logo-mark.svg" if (ROOT / "webui/static/brand/logo-mark.svg").exists() else "",
        f"--add-data=webui{os.pathsep}webui",  # Inclui templates e static
        f"--add-data=config.json{os.pathsep}.",  # Inclui config padrão
        "--hidden-import=pynetdicom",
        "--hidden-import=pydicom",
        "--hidden-import=flask",
        "--hidden-import=oracledb",
        "--hidden-import=pymysql",
        "--collect-all=pynetdicom",
        "--collect-all=pydicom",
        "--collect-all=flask",
        "startapp.py"
    ]
    
    # Remover argumentos vazios
    cmd = [arg for arg in cmd if arg]
    
    try:
        subprocess.check_call(cmd)
        
        print("\n" + "="*60)
        print("✓ BUILD CONCLUÍDO COM SUCESSO!")
        print("="*60)
        
        exe_path = dist_dir / "FlowWorklist.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"\n📁 Executável gerado: {exe_path}")
            print(f"📏 Tamanho: {size_mb:.1f} MB")
            print("\n🚀 COMO USAR:")
            print("   1. Copie FlowWorklist.exe para o servidor")
            print("   2. Copie config.json e edite com suas credenciais")
            print("   3. Execute FlowWorklist.exe")
            print("   4. Acesse http://localhost:5000")
            print("\n💡 DICA: Use NSSM para instalar como serviço Windows")
            print("   nssm install FlowWorklist \"C:\\Path\\To\\FlowWorklist.exe\"")
            return True
        else:
            print("\n✗ Executável não foi gerado")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"\n✗ ERRO durante build: {e}")
        return False
    except Exception as e:
        print(f"\n✗ ERRO inesperado: {e}")
        return False

def build_service_only():
    """Gera executável apenas do serviço DICOM (sem UI)"""
    print("\n" + "="*60)
    print("FlowWorklist - Build Serviço DICOM (CLI)")
    print("="*60 + "\n")
    
    if not check_pyinstaller():
        return False
    
    dist_dir = ROOT / "dist"
    
    print("\n📦 Gerando executável do serviço...")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=FlowWorklist-Service",
        "--onefile",
        "--console",  # Mantém console para logs
        f"--add-data=config.json{os.pathsep}.",
        "--hidden-import=pynetdicom",
        "--hidden-import=pydicom",
        "--hidden-import=oracledb",
        "--hidden-import=pymysql",
        "--collect-all=pynetdicom",
        "--collect-all=pydicom",
        "mwl_service.py"
    ]
    
    cmd = [arg for arg in cmd if arg]
    
    try:
        subprocess.check_call(cmd)
        
        print("\n✓ Serviço DICOM gerado com sucesso!")
        exe_path = dist_dir / "FlowWorklist-Service.exe"
        if exe_path.exists():
            print(f"📁 {exe_path}")
            print("\n🚀 Execute: FlowWorklist-Service.exe")
            return True
            
    except Exception as e:
        print(f"✗ Erro: {e}")
        return False

if __name__ == "__main__":
    print("\nEscolha o tipo de build:")
    print("1. Completo (Dashboard + Serviço DICOM)")
    print("2. Apenas Serviço DICOM (CLI)")
    print("3. Ambos")
    
    choice = input("\nOpção [1-3]: ").strip()
    
    success = True
    
    if choice == "1":
        success = build_executable()
    elif choice == "2":
        success = build_service_only()
    elif choice == "3":
        success = build_executable() and build_service_only()
    else:
        print("Opção inválida")
        success = False
    
    if not success:
        sys.exit(1)
    
    print("\n✓ Processo concluído!")
    input("\nPressione ENTER para sair...")
