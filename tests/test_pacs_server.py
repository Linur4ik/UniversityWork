"""
Тестовый PACS сервер для проверки функционала отправки/приема
"""
from pynetdicom import AE, StoragePresentationContexts, evt
from pynetdicom.sop_class import (
    CTImageStorage, MRImageStorage, UltrasoundImageStorage,
    SecondaryCaptureImageStorage, ComputedRadiographyImageStorage
)
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('pynetdicom')

def handle_store(event):
    """Обработчик события C-STORE"""
    logger.info(f"Получен C-STORE запрос для SOP Class: {event.request.AffectedSOPClassUID}")
    logger.info(f"SOP Instance UID: {event.request.AffectedSOPInstanceUID}")
    
    # Сохраняем полученный файл
    ds = event.dataset
    ds.file_meta = event.file_meta
    
    filename = f"received_{ds.SOPInstanceUID}.dcm" if hasattr(ds, 'SOPInstanceUID') else "received.dcm"
    ds.save_as(filename, write_like_original=False)
    logger.info(f"Файл сохранен как: {filename}")
    
    return 0x0000  # Success

def main():
    # Создаем Application Entity
    ae = AE(ae_title='TEST_PACS_SERVER')
    
    # Добавляем поддерживаемые контексты представления
    ae.supported_contexts = StoragePresentationContexts
    
    handlers = [(evt.EVT_C_STORE, handle_store)]
    
    # Запускаем сервер
    print("Тестовый PACS сервер запущен")
    print("AE Title: TEST_PACS_SERVER")
    print("Порт: 11112")
    print("Ожидание подключений...")
    
    ae.start_server(('', 11112), evt_handlers=handlers)

if __name__ == "__main__":
    main()