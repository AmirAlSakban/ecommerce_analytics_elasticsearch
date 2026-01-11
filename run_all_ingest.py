"""Run all ingestion pipelines in sequence."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from settings import configure_logging, get_settings

from ingest_orders import ingest_orders
from ingest_products import bulk_index_products
from ingest_returns import ingest_returns

logger = logging.getLogger(__name__)


def check_elasticsearch_connection() -> bool:
    """Check if Elasticsearch is running and accessible."""
    import warnings
    warnings.filterwarnings('ignore', message='.*Node.*has failed.*')
    warnings.filterwarnings('ignore', message='.*Retrying request.*')
    
    # Temporarily suppress elastic_transport logging
    es_logger = logging.getLogger('elastic_transport')
    original_level = es_logger.level
    es_logger.setLevel(logging.CRITICAL)
    
    try:
        from elasticsearch import Elasticsearch
        settings = get_settings()
        # Disable retries for faster check
        client = Elasticsearch(
            settings.es_url, 
            basic_auth=settings.es_basic_auth,
            retry_on_timeout=False,
            max_retries=0,
            request_timeout=2
        )
        client.info()
        return True
    except Exception:
        return False
    finally:
        es_logger.setLevel(original_level)


def open_file_dialog(title: str = "Selectează fișierul", filetypes: tuple = None, message: str = None) -> Optional[Path]:
    """Open a file dialog to select a file with an informative message box."""
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox
        
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        root.attributes('-topmost', True)  # Bring dialog to front
        
        # Show info message if provided
        if message:
            messagebox.showinfo("Selectare fișier", message, parent=root)
        
        if filetypes is None:
            filetypes = (
                ("Excel files", "*.xlsx *.xls"),
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            )
        
        initial_dir = Path.cwd() / "data" / "raw"
        if not initial_dir.exists():
            initial_dir = Path.cwd()
        
        file_path = filedialog.askopenfilename(
            title=title,
            filetypes=filetypes,
            initialdir=initial_dir
        )
        
        root.destroy()
        
        if file_path:
            logger.info(f"✓ Fișier selectat: {file_path}")
            return Path(file_path)
        else:
            logger.info("Selectare anulată de utilizator")
            return None
    except Exception as e:
        logger.error(f"Nu s-a putut deschide dialogul de selectare fișier: {e}")
        return None
DEFAULT_PATTERNS = {
    "products": "products_*.xlsx",
    "orders": "orders_*.csv",
    "returns": "returns_*.csv",
}


def resolve_path(value: Optional[str], pattern: str, allow_dialog: bool = False, 
                 dialog_title: str = "Selectează fișierul", dialog_message: str = None,
                 optional: bool = False) -> Optional[Path]:
    if not value:
        if allow_dialog:
            logger.info("📂 Deschid dialogul de selectare fișier...")
            selected = open_file_dialog(title=dialog_title, message=dialog_message)
            if selected:
                return selected
            if optional:
                logger.info("Sar peste acest pas")
                return None
        if optional:
            return None
        raise FileNotFoundError("Setează căile fișierelor în local_settings.json sau prin argumente.")
    
    candidate = Path(value)
    if candidate.is_file():
        logger.info(f"✓ Folosesc fișierul: {candidate}")
        return candidate
    if candidate.is_dir():
        matches = sorted(candidate.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
        if matches:
            logger.info(f"✓ Găsit automat: {matches[0]}")
            return matches[0]
    # Treat as glob pattern relative to repo root
    matches = sorted(Path.cwd().glob(value), key=lambda p: p.stat().st_mtime, reverse=True)
    if matches:
        logger.info(f"✓ Găsit automat: {matches[0]}")
        return matches[0]
    
    # File not found - offer dialog as fallback
    if allow_dialog:
        logger.warning(f"⚠ Nu am găsit fișier pentru {value}")
        logger.info("📂 Deschid dialogul de selectare...")
        selected = open_file_dialog(title=dialog_title, message=dialog_message)
        if selected:
            return selected
        if optional:
            logger.info("Sar peste acest pas")
            return None
    
    if optional:
        return None
    raise FileNotFoundError(f"Nu am găsit fișier pentru {value}")


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description="Rulează ingestia de produse, comenzi și retururi")
    parser.add_argument("--products", type=str, help="Cale sau director/glob pentru exportul de produse")
    parser.add_argument("--orders", type=str, help="Cale sau director/glob pentru exportul de comenzi")
    parser.add_argument("--returns", type=str, help="Cale sau director/glob pentru exportul de retururi")
    parser.add_argument("--skip-orders", action="store_true", help="Sari peste ingestia de comenzi")
    parser.add_argument("--skip-returns", action="store_true", help="Sari peste ingestia de retururi")
    parser.add_argument("--use-dialog", action="store_true", help="Deschide dialog pentru selectarea fișierelor")
    args = parser.parse_args()

    settings = get_settings()

    logger.info("=" * 70)
    logger.info("🚀 INGESTIE DATE - Ecommerce Analytics")
    logger.info("=" * 70)
    
    # Check Elasticsearch connection first
    logger.info("\n🔌 Verificare conexiune Elasticsearch...")
    if not check_elasticsearch_connection():
        logger.error("\n" + "=" * 70)
        logger.error("❌ EROARE: Nu pot conecta la Elasticsearch!")
        logger.error("=" * 70)
        logger.error("\n📋 Pași pentru pornire Elasticsearch:")
        logger.error("   1. Deschide un terminal nou")
        logger.error("   2. Navighează la: cd out/elasticsearch/elasticsearch-8.15.2")
        logger.error("   3. Pornește serverul: bin\\elasticsearch.bat")
        logger.error("   4. Așteaptă mesajul 'started' (poate dura 30-60 secunde)")
        logger.error("   5. Rulează din nou acest script\n")
        logger.error("💡 TIP: Lasă terminalul cu Elasticsearch deschis în timpul ingestiei")
        logger.error("=" * 70 + "\n")
        sys.exit(1)
    
    logger.info("✅ Elasticsearch este activ și accesibil\n")
    
    logger.info("📦 PASUL 1/3: Selectare fișier PRODUSE (OBLIGATORIU)")
    products_path = resolve_path(
        args.products or settings.data_paths.products_export,
        DEFAULT_PATTERNS["products"],
        allow_dialog=args.use_dialog,
        dialog_title="PASUL 1: Selectează fișierul Excel cu PRODUSE",
        dialog_message="Selectează fișierul Excel cu datele de produse.\n\n"
                      "Fișierul trebuie să conțină coloanele:\n"
                      "• Cod Produs (SKU)\n"
                      "• Denumire Produs\n"
                      "• și alte atribute opționale"
    )

    orders_path = None
    if not args.skip_orders:
        logger.info("\n📊 PASUL 2/3: Selectare fișier COMENZI (OPȚIONAL)")
        orders_source = args.orders or settings.data_paths.orders_export
        if orders_source or args.use_dialog:
            orders_path = resolve_path(
                orders_source, 
                DEFAULT_PATTERNS["orders"],
                allow_dialog=args.use_dialog,
                dialog_title="PASUL 2: Selectează fișierul CSV cu COMENZI (opțional)",
                dialog_message="Selectează fișierul CSV cu datele de comenzi.\n\n"
                              "Poți anula (Cancel) pentru a sări peste acest pas.",
                optional=True
            )

    returns_path = None
    if not args.skip_returns:
        logger.info("\n🔄 PASUL 3/3: Selectare fișier RETURURI (OPȚIONAL)")
        returns_source = args.returns or settings.data_paths.returns_export
        if returns_source or args.use_dialog:
            returns_path = resolve_path(
                returns_source, 
                DEFAULT_PATTERNS["returns"],
                allow_dialog=args.use_dialog,
                dialog_title="PASUL 3: Selectează fișierul CSV cu RETURURI (opțional)",
                dialog_message="Selectează fișierul CSV cu datele de retururi.\n\n"
                              "Poți anula (Cancel) pentru a sări peste acest pas.",
                optional=True
            )

    logger.info("\n" + "=" * 70)
    logger.info("🔄 Încep procesarea fișierelor...")
    logger.info("=" * 70)
    
    logger.info("\n📦 INGESTIE PRODUSE din %s", products_path)
    product_stats = bulk_index_products(products_path)
    logger.info("✅ Produse procesate: %s", product_stats)

    if orders_path:
        logger.info("\n📊 INGESTIE COMENZI din %s", orders_path)
        order_stats = ingest_orders(orders_path)
        logger.info("✅ Comenzi procesate: %s", order_stats)
    else:
        logger.info("\n⏭ Ingestia comenzilor a fost sărită")

    if returns_path:
        logger.info("\n🔄 INGESTIE RETURURI din %s", returns_path)
        return_stats = ingest_returns(returns_path)
        logger.info("✅ Retururi procesate: %s", return_stats)
    else:
        logger.info("\n⏭ Ingestia retururilor a fost sărită")

    logger.info("\n" + "=" * 70)
    logger.info("✅ INGESTIE COMPLETĂ - Toate fișierele au fost procesate!")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
