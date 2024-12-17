import requests
from bs4 import BeautifulSoup
import time
import csv
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

# Crear estructura de directorios si no existe
Path("data/csv").mkdir(parents=True, exist_ok=True)
Path("logs").mkdir(parents=True, exist_ok=True)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,  # Cambiado a INFO para reducir el ruido en logs
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/scraper_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

class SernatutScraper:
    def __init__(self):
        self.base_url = "https://serviciosturisticos.sernatur.cl/nueva_busqueda.php"
        self.detail_base_url = "https://serviciosturisticos.sernatur.cl"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def _clean_phone(self, phone: str) -> str:
        """Limpia y formatea un número de teléfono."""
        # Extraer solo la parte que contiene el número
        if ':' in phone:
            phone = phone.split(':', 1)[1]
        
        # Eliminar texto común que no es parte del número
        phone = phone.replace('Teléfono', '').replace('telefono', '')
        
        # Limpiar caracteres no deseados
        cleaned = ''.join(c for c in phone if c.isdigit() or c in ['+', ' '])
        cleaned = cleaned.strip()
        
        # Si no hay números, retornar None
        if not any(c.isdigit() for c in cleaned):
            return None
            
        # Formatear el número
        if cleaned.startswith('56'):
            cleaned = '+' + cleaned
        elif cleaned.startswith('9'):
            cleaned = '+56' + cleaned
        
        return cleaned

    def _process_guide_box(self, caja) -> Optional[Dict]:
        """Procesa una caja individual de guía y obtiene sus detalles."""
        try:
            detail_link = caja.select_one('a.sig')
            if not detail_link:
                return None

            detail_url = self.detail_base_url + detail_link['href']
            logging.info(f"Procesando guía en: {detail_url}")

            detail_resp = self.session.get(detail_url)
            detail_resp.raise_for_status()
            detail_soup = BeautifulSoup(detail_resp.text, "html.parser")

            # Extraer toda la información del guía
            guide_info = {
                'detail_url': detail_url,
                'personal_info': {
                    'name': None,
                    'email': None,
                    'phone': None
                },
                'location': {
                    'comuna': None,
                    'localidad': None,
                    'region': None
                },
                'registration': {
                    'type': None,
                    'status': None,
                    'specialties': []
                }
            }

            # Obtener nombre
            name_tag = detail_soup.select_one('h4.nombre.tituloperfil')
            if name_tag:
                guide_info['personal_info']['name'] = name_tag.get_text(strip=True)

            # Procesar todos los párrafos para extraer información
            all_paragraphs = detail_soup.find_all('p')
            
            for p in all_paragraphs:
                text = p.text.strip()
                if not text:
                    continue

                lines = [line.strip() for line in text.split('\n') if line.strip()]
                
                for line in lines:
                    line_lower = line.lower()
                    
                    if 'comuna:' in line_lower:
                        guide_info['location']['comuna'] = line.split(':', 1)[1].strip()
                    elif 'localidad:' in line_lower:
                        guide_info['location']['localidad'] = line.split(':', 1)[1].strip()
                    elif 'región:' in line_lower:
                        guide_info['location']['region'] = line.split(':', 1)[1].strip()
                    elif any(phone in line_lower for phone in ['teléfono:', 'telefono:', '(56)', '+56']) and guide_info['personal_info']['phone'] is None:
                        phone = self._clean_phone(line)
                        if phone:  # Solo asignar si se encontró un número válido
                            guide_info['personal_info']['phone'] = phone
                            logging.debug(f"Teléfono encontrado: {phone}")
                    elif '@' in line and not any(info in line_lower for info in ['comuna:', 'región:', 'localidad:', 'teléfono:']):
                        guide_info['personal_info']['email'] = line.strip()
                    elif 'registro vigente' in line_lower:
                        guide_info['registration']['status'] = 'VIGENTE'
                    elif 'especializado en' in line_lower:
                        especialidad = line.split('en', 1)[1].strip()
                        if especialidad and especialidad not in guide_info['registration']['specialties']:
                            guide_info['registration']['specialties'].append(especialidad)
                    elif 'general' in line_lower and len(line.strip()) < 10:
                        guide_info['registration']['type'] = 'General'

            return guide_info

        except requests.RequestException as e:
            logging.error(f"Error al obtener detalles del guía: {str(e)}")
            return None
        except Exception as e:
            logging.error(f"Error inesperado procesando guía: {str(e)}")
            return None

    def save_to_csv(self, guides: List[Dict], filename: str):
        """Guarda los resultados en formato CSV."""
        fieldnames = [
            'name', 'email', 'phone', 'comuna', 'localidad', 'region',
            'registration_type', 'specialties', 'status', 'detail_url'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for guide in guides:
                flat_guide = {
                    'name': guide['personal_info']['name'],
                    'email': guide['personal_info']['email'],
                    'phone': guide['personal_info']['phone'],
                    'comuna': guide['location']['comuna'],
                    'localidad': guide['location']['localidad'],
                    'region': guide['location']['region'],
                    'registration_type': guide['registration']['type'],
                    'specialties': json.dumps(guide['registration']['specialties'], ensure_ascii=False) if guide['registration']['specialties'] else '[]',
                    'status': guide['registration']['status'],
                    'detail_url': guide['detail_url']
                }
                writer.writerow(flat_guide)
        logging.info(f"Datos guardados en CSV: {filename}")

    def get_guides(self, tipo_servicio: int, region: int, sleep_time: float = 1.0,
                 max_pages: Optional[int] = None, max_results: Optional[int] = None) -> List[Dict]:
        """
        Obtiene los guías para un tipo de servicio y región específicos.
        
        Args:
            tipo_servicio: ID del tipo de servicio (ej: 16 para guías de turismo)
            region: ID de la región (ej: 13 para RM)
            sleep_time: Tiempo de espera entre requests en segundos
            max_pages: Si se especifica, límite máximo de páginas a procesar
            max_results: Si se especifica, número máximo de resultados a obtener
            
        Returns:
            Lista de diccionarios con información de los guías
        """
        params = {
            'page': 1,
            'tipo_servicio': tipo_servicio,
            'clase_servicio': 0,
            'region': region,
            'comuna': 0,
            'nombre': '',
            'selloq': '',
            'sellos': '',
            'sellop': '',
            'sellobp': ''
        }
        
        all_guides = []
        
        while True:
            try:
                if max_pages and params['page'] > max_pages:
                    logging.info(f"Alcanzado el límite de páginas: {max_pages}")
                    break

                logging.info(f"Obteniendo página {params['page']}...")
                r = self.session.get(self.base_url, params=params)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "html.parser")

                cajas = soup.select('.main_caja')
                if not cajas:
                    logging.info("No se encontraron más resultados")
                    break

                for caja in cajas:
                    if max_results and len(all_guides) >= max_results:
                        logging.info(f"Alcanzado el límite de resultados: {max_results}")
                        return all_guides

                    guide_info = self._process_guide_box(caja)
                    if guide_info:
                        all_guides.append(guide_info)
                        if len(all_guides) % 10 == 0:  # Log cada 10 guías
                            logging.info(f"Procesados {len(all_guides)} guías...")
                    time.sleep(sleep_time)  # Aumentado para ser más respetuosos con el servidor

                if not self._has_next_page(soup, params['page']):
                    break
                    
                params['page'] += 1
                
            except requests.RequestException as e:
                logging.error(f"Error al obtener la página {params['page']}: {str(e)}")
                break
            except Exception as e:
                logging.error(f"Error inesperado en página {params['page']}: {str(e)}")
                break

        return all_guides

    def _has_next_page(self, soup: BeautifulSoup, current_page: int) -> bool:
        """Verifica si existe una página siguiente."""
        paginacion = soup.select_one('#paginacion')
        if not paginacion:
            return False
        
        next_page_link = paginacion.find('a', href=True, text=str(current_page + 1))
        return bool(next_page_link)

def main():
    scraper = SernatutScraper()
    
    # Configuración para una prueba más grande
    guides = scraper.get_guides(
        tipo_servicio=16,  # Guías de turismo
        region=13,         # Región Metropolitana
        sleep_time=1.0,    # 1 segundo entre requests
        max_results=10    # Obtener 100 resultados
    )
    
    if guides:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data/csv/guias_turismo_{timestamp}.csv"
        scraper.save_to_csv(guides, filename)
        logging.info(f"Scraping completo. Se encontraron {len(guides)} guías")
    else:
        logging.warning("No se encontraron guías")

if __name__ == "__main__":
    main() 