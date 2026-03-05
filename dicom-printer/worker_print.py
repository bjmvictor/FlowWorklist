import time
import subprocess
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

DCMTK_BIN = Path(r"C:\dcmtk\bin")
DB_DIR = Path(r"C:\dicom-print\database")
OUT_DIR = Path(r"C:\dicom-print\out")
OUT_DIR.mkdir(parents=True, exist_ok=True)

SUMATRA = Path(r"C:\Program Files\SumatraPDF\SumatraPDF.exe")
PRINTER_NAME = "XEROX"

DELETE_AFTER_SUCCESS = False
SP_TIME_WINDOW_SECONDS = 120  # apaga SP próximo ao HG (janela de tempo)

def wait_stable(path: Path, timeout=20):
    start = time.time()
    last = -1
    while time.time() - start < timeout:
        try:
            size = path.stat().st_size
        except FileNotFoundError:
            time.sleep(0.2)
            continue
        if size > 0 and size == last:
            return True
        last = size
        time.sleep(0.3)
    return False

def safe_delete(p: Path):
    try:
        if p and p.exists():
            p.unlink()
    except Exception as e:
        print(f"[WARN] Não consegui apagar {p.name}: {e}")

def dicom_to_png(dcm_path: Path) -> Path:
    out_png = OUT_DIR / (dcm_path.stem + ".png")
    dcm2img = str(DCMTK_BIN / "dcm2img.exe")
    subprocess.run([dcm2img, "+on", "--write-png", str(dcm_path), str(out_png)],
                   check=True, capture_output=True, text=True)
    return out_png

def png_to_pdf(png_path: Path) -> Path:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A3
    from reportlab.lib.utils import ImageReader

    pdf_path = png_path.with_suffix(".pdf")
    img = ImageReader(str(png_path))
    iw, ih = img.getSize()

    w, h = A3  # A3 retrato; para paisagem use: (h, w)
    c = canvas.Canvas(str(pdf_path), pagesize=(w, h))

    # margem mínima para evitar áreas não imprimíveis / branco no driver
    m = 0  # pontos (~4,2mm). Se quiser, aumente para 18-24.

    # FIT: não corta, mantém proporção
    scale = min((w - 2*m) / iw, (h - 2*m) / ih)
    nw, nh = iw * scale, ih * scale

    x = (w - nw) / 2
    y = (h - nh) / 2

    c.drawImage(img, x, y, width=nw, height=nh, preserveAspectRatio=True, mask="auto")
    c.showPage()
    c.save()
    return pdf_path

def print_pdf(pdf_path: Path):
    if not SUMATRA.exists():
        raise RuntimeError("SumatraPDF não encontrado. Ajuste o caminho SUMATRA.")
    cmd = [str(SUMATRA)]
    if PRINTER_NAME:
        cmd += ["-print-to", PRINTER_NAME]
    #cmd += ["-silent", "-print-settings", "noscale", str(pdf_path)]
    cmd += ["-silent", "-print-settings", "fit", str(pdf_path)]
    #cmd += ["-silent", "-print-settings", "shrink", str(pdf_path)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Falha ao imprimir (code={res.returncode}): {res.stderr.strip() or res.stdout.strip()}")

def delete_related_sp_by_time(time_center: float):
    deleted = 0
    for sp in DB_DIR.glob("SP_*.dcm"):
        try:
            dt = abs(sp.stat().st_mtime - time_center)
            if dt <= SP_TIME_WINDOW_SECONDS:
                safe_delete(sp)
                deleted += 1
        except Exception:
            pass
    if deleted:
        print(f"[OK] SP apagados: {deleted}")

def process_hg(hg_path: Path):
    if not wait_stable(hg_path):
        return

    png = pdf = None
    try:
        t_center = hg_path.stat().st_mtime
        png = dicom_to_png(hg_path)
        pdf = png_to_pdf(png)
        print_pdf(pdf)
        print(f"[OK] Impresso: {hg_path.name}")

        if DELETE_AFTER_SUCCESS:
            safe_delete(pdf)
            safe_delete(png)
            safe_delete(hg_path)
            delete_related_sp_by_time(t_center)

    except Exception as e:
        print(f"[ERRO] {hg_path.name}: {e}")

class Handler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        p = Path(event.src_path)
        if p.suffix.lower() == ".dcm" and p.name.upper().startswith("HG_"):
            process_hg(p)

if __name__ == "__main__":
    print("Worker monitorando:", DB_DIR)
    obs = Observer()
    obs.schedule(Handler(), str(DB_DIR), recursive=False)
    obs.start()
    try:
        while True:
            time.sleep(1)
    finally:
        obs.stop()
        obs.join()