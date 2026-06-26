# -*- coding: utf-8 -*-
from qgis.PyQt.QtWidgets import (QAction, QMessageBox, QListWidget, QPushButton, 
                                 QVBoxLayout, QDialog, QLabel, QProgressBar, 
                                 QHBoxLayout, QFrame, QSpacerItem, QSizePolicy,
                                 QCheckBox, QLineEdit, QGroupBox, QDialogButtonBox)
from qgis.PyQt.QtGui import QIcon, QFont, QPixmap
from qgis.PyQt.QtCore import Qt, QThread, pyqtSignal, QSettings
from qgis.core import QgsProject, QgsRasterLayer, QgsMessageLog, Qgis, QgsDataSourceUri
from PyQt5 import uic
from qgis.PyQt.QtCore import QEvent
import os
import requests
from defusedxml import ElementTree as ET
import base64

class LayerLoadWorker(QThread):
    """Worker thread para carregar camadas em background"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, layers, usuario, senha):
        super().__init__()
        self.layers = layers
        self.usuario = usuario
        self.senha = senha
        
    def run(self):
        loaded_layers = []
        total = len(self.layers)
        
        for i, layer_name in enumerate(self.layers):
            try:
                # Criar URI sem credenciais expostas na URL
                uri = QgsDataSourceUri()
                uri.setParam("url", "http://srv1185637.hstgr.cloud:8082/geoserver/ASSINATURA_PA/wms")
                uri.setParam("crs", "EPSG:4674")
                uri.setParam("format", "image/png")
                uri.setParam("layers", layer_name)
                uri.setParam("styles", "")
                
                # Configurar autenticação de forma segura
                uri.setParam("username", self.usuario)
                uri.setParam("password", self.senha)
                
                # Criar camada raster com URI segura
                raster_layer = QgsRasterLayer(uri.encodedUri().data().decode(), 
                                            layer_name.replace("ASSINATURA_PA:", ""), "wms")
                
                if raster_layer.isValid():
                    QgsProject.instance().addMapLayer(raster_layer)
                    loaded_layers.append(layer_name)
                    
                progress_value = int((i + 1) / total * 100)
                self.progress.emit(progress_value)
                
            except Exception as e:
                self.error.emit(f"Erro ao carregar {layer_name}: {str(e)}")
                
        self.finished.emit(loaded_layers)



class LayerListDialog(QDialog):
    """Diálogo customizado para a lista de camadas que captura o evento de tecla."""
    def __init__(self, parent=None, load_layers_callback=None, logout_callback=None, user_name=""):
        super().__init__(parent)
        self.load_layers_callback = load_layers_callback
        self.logout_callback = logout_callback
        self.user_name = user_name
        self.btn_carregar = None
        self.list_widget = None
        self.search_box = None
        self.progress_frame = None
        self.progress_bar = None
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Camadas Disponíveis - Geoserviço")
        self.setFixedSize(600, 500)
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #495057;
            }
            QListWidget {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                background-color: #f8f9fa;
                selection-background-color: #0d6efd;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #e9ecef;
            }
            QListWidget::item:hover {
                background-color: #e3f2fd;
            }
            QPushButton {
                padding: 12px 24px;
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
            QCheckBox {
                font-size: 13px;
                color: #495057;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                font-size: 13px;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        
        # Header com logo e informações de usuário
        header_frame = QFrame()
        header_layout = QHBoxLayout(header_frame)
        
        # Título e informações do usuário
        title_info_layout = QVBoxLayout()
        title_label = QLabel("Camadas Disponíveis")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        
        user_label = QLabel(f"Usuário: {self.user_name}")
        user_label.setStyleSheet("color: #6c757d; font-size: 12px;")
        
        title_info_layout.addWidget(title_label)
        title_info_layout.addWidget(user_label)
        
        # Botão de logout
        logout_button = QPushButton("Logout")
        logout_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        logout_button.clicked.connect(lambda: self.logout_callback(self))
        
        header_layout.addLayout(title_info_layout)
        header_layout.addStretch()
        header_layout.addWidget(logout_button)
        
        main_layout.addWidget(header_frame)
        
        # Filtro de busca
        search_group = QGroupBox("Filtrar Camadas")
        search_layout = QVBoxLayout(search_group)
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Digite para filtrar camadas...")
        search_layout.addWidget(self.search_box)
        
        main_layout.addWidget(search_group)
        
        # Lista de camadas
        layers_group = QGroupBox(f"Camadas Encontradas") # O número será atualizado no GeoservicoInsumosPlugin
        layers_group.setObjectName("layers_group") # Adicionado para permitir o findChild
        layers_layout = QVBoxLayout(layers_group)
        
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.MultiSelection)
        
        layers_layout.addWidget(self.list_widget)
        main_layout.addWidget(layers_group)
        
        # Controles
        controls_layout = QHBoxLayout()
        controls_layout.addStretch()
        
        self.btn_carregar = QPushButton("Carregar Selecionadas")
        self.btn_carregar.setEnabled(False)
        self.btn_carregar.clicked.connect(self.load_layers_callback)
        controls_layout.addWidget(self.btn_carregar)
        
        main_layout.addLayout(controls_layout)
        
        # Barra de progresso (inicialmente oculta)
        self.progress_frame = QFrame()
        progress_layout = QVBoxLayout(self.progress_frame)
        progress_label = QLabel("Carregando camadas...")
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(progress_label)
        progress_layout.addWidget(self.progress_bar)
        self.progress_frame.hide()
        
        main_layout.addWidget(self.progress_frame)

    def keyPressEvent(self, event):
        """Captura o evento de tecla para carregar camadas com ENTER."""
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self.btn_carregar and self.btn_carregar.isEnabled():
                self.load_layers_callback()
                event.accept()
                return
        super().keyPressEvent(event)

class GeoservicoInsumosPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.login_dialog = None
        self.camadas = []
        self.usuario = None
        self.senha = None
        self.worker = None
        self.settings = QSettings("Geoservico", "InsumosPlugin")
        self.is_authenticated = False  # Estado de autenticação
        self.auth_session = None  # Sessão de autenticação
        self.current_layer_dialog = None # Referência ao diálogo de camadas atual

    def initGui(self):
        self.action = QAction(QIcon(os.path.join(self.plugin_dir, "icon.png")),
                              "Geoserviço - Catálogo de Insumos por Assinatura-PA", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("Geoserviço", self.action)

    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        self.iface.removePluginMenu("Geoserviço", self.action)
        # Limpar estado de autenticação ao descarregar o plugin
        self.is_authenticated = False
        self.auth_session = None

    def is_user_authenticated(self):
        """Verifica se o usuário está autenticado"""
        return self.is_authenticated and self.usuario and self.senha

    def validate_authentication(self):
        """Valida se a autenticação ainda é válida"""
        if not self.is_user_authenticated():
            return False
            
        try:
            # Testa a conexão com as credenciais atuais
            url_capabilities = "http://srv1185637.hstgr.cloud:8082/geoserver/ASSINATURA_PA/ows?service=WMS&version=1.3.0&request=GetCapabilities"
            r = requests.get(url_capabilities, auth=(self.usuario, self.senha), timeout=10)
            r.raise_for_status()
            return True
        except:
            # Se falhar, limpar estado de autenticação
            self.is_authenticated = False
            self.auth_session = None
            return False

    def run(self):
        # 1. Tentar carregar credenciais salvas
        saved_user = self.settings.value("username", "")
        saved_pass = self.settings.value("password", "")
        
        if saved_user and saved_pass:
            self.usuario = saved_user
            self.senha = saved_pass
            self.is_authenticated = True # Assumir autenticado para tentar validar

        # 2. Verificar se está autenticado e validar
        if self.is_user_authenticated() and self.validate_authentication():
            # Se já está autenticado, mostrar diretamente a lista de camadas
            if self.camadas:
                self.show_layer_list()
            else:
                # Recarregar camadas se necessário
                self.load_available_layers()
        else:
            # Se a autenticação falhou ou não havia credenciais salvas, mostrar diálogo de login
            self.show_login_dialog()

    def show_login_dialog(self):
        """Exibe o diálogo de login"""
        ui_path = os.path.join(self.plugin_dir, "form_login.ui")
        self.login_dialog = uic.loadUi(ui_path)
        
        # Tentar carregar credenciais salvas
        saved_user = self.settings.value("username", "")
        if saved_user:
            self.login_dialog.lineUser.setText(saved_user)
            self.login_dialog.saveCredentialsCheckBox.setChecked(True)

        # Informar ao usuário sobre o salvamento
        self.login_dialog.saveCredentialsCheckBox.setText("Salvar login e senha")

        # Configurar estilo do diálogo de login
        self.login_dialog.setFixedSize(400, 300)
        self.login_dialog.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
                border-radius: 8px;
            }
            QLineEdit {
                padding: 12px;
                border: 2px solid #e9ecef;
                border-radius: 6px;
                font-size: 14px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #0d6efd;
                outline: none;
            }
            QPushButton {
                padding: 10px 20px;
                background-color: #0d6efd;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0b5ed7;
            }
            QPushButton:pressed {
                background-color: #0a58ca;
            }
            QLabel {
                color: #495057;
            }
        """)
        
        self.login_dialog.buttonBox.accepted.connect(self.do_login)
        self.login_dialog.buttonBox.rejected.connect(self.login_dialog.reject)
        
        # Adicionar botão minimizar
        minimize_button = QPushButton("Minimizar")
        minimize_button.clicked.connect(self.login_dialog.showMinimized)
        self.login_dialog.buttonBox.addButton(minimize_button, QDialogButtonBox.ActionRole)

        self.login_dialog.setModal(False)
        self.login_dialog.show()

    def do_login(self):
        """Realiza o processo de login"""
        self.usuario = self.login_dialog.lineUser.text().strip()
        self.senha = self.login_dialog.linePass.text().strip()
        save_credentials = self.login_dialog.saveCredentialsCheckBox.isChecked()

        # 1. Tentar autenticar com as credenciais fornecidas
        if not self.usuario or not self.senha:
            QMessageBox.warning(None, "Aviso", "Por favor, preencha usuário e senha.")
            return

        # Mostrar diálogo de progresso
        progress_dialog = QDialog()
        progress_dialog.setWindowTitle("Conectando...")
        progress_dialog.setFixedSize(300, 100)
        progress_dialog.setModal(True)
        
        layout = QVBoxLayout(progress_dialog)
        label = QLabel("Verificando credenciais...")
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 0)  # Indeterminado
        
        layout.addWidget(label)
        layout.addWidget(progress_bar)
        progress_dialog.show()

        if self.authenticate_user():
            progress_dialog.close()
            self.login_dialog.accept()
            
            # 2. Se a autenticação for bem-sucedida, salvar/remover credenciais
            if save_credentials:
                self.settings.setValue("username", self.usuario)
                self.settings.setValue("password", self.senha)
                QgsMessageLog.logMessage("Credenciais salvas no QSettings.", "Geoserviço", Qgis.Info)
            else:
                self.settings.remove("username")
                self.settings.remove("password")
                QgsMessageLog.logMessage("Credenciais removidas do QSettings.", "Geoserviço", Qgis.Info)

            self.load_available_layers()
        else:
            progress_dialog.close()
            QMessageBox.critical(None, "Erro de Autenticação", 
                               "Credenciais inválidas ou erro de conexão.\n\nVerifique suas credenciais e conexão com a internet.")

    def authenticate_user(self):
        """Autentica o usuário no servidor"""
        try:
            url_capabilities = "http://srv1185637.hstgr.cloud:8082/geoserver/ASSINATURA_PA/ows?service=WMS&version=1.3.0&request=GetCapabilities"
            r = requests.get(url_capabilities, auth=(self.usuario, self.senha), timeout=15)
            r.raise_for_status()
            
            # Se chegou até aqui, a autenticação foi bem-sucedida
            self.is_authenticated = True
            self.auth_session = r  # Armazenar a sessão para referência
            return True
            
        except Exception as e:
            self.is_authenticated = False
            self.auth_session = None
            QgsMessageLog.logMessage(f"Erro de autenticação: {str(e)}", "Geoserviço", Qgis.Warning)
            return False

    def load_available_layers(self):
        """Carrega a lista de camadas disponíveis (apenas se autenticado)"""
        if not self.is_user_authenticated():
            QMessageBox.warning(None, "Acesso Negado", 
                              "Você precisa estar logado para acessar as camadas.\n\nFaça login primeiro.")
            return

        try:
            url_capabilities = "http://srv1185637.hstgr.cloud:8082/geoserver/ASSINATURA_PA/ows?service=WMS&version=1.3.0&request=GetCapabilities"
            r = requests.get(url_capabilities, auth=(self.usuario, self.senha), timeout=15)
            r.raise_for_status()
            
            root = ET.fromstring(r.content)
            # Definir os namespaces WMS e WMS-T (se aplicável)
            namespaces = {
                "wms": "http://www.opengis.net/wms",
                "wms_t": "http://www.opengis.net/wms-t" # Adicionado para robustez
            }
            
            # Limpar lista de camadas anterior
            self.camadas = []
            
            # Buscar todas as tags <Layer> dentro da tag <Capability> usando XPath com namespace
            # O XPath //wms:Layer/wms:Layer busca camadas aninhadas, ignorando a camada raiz
            layers_xpath = ".//wms:Layer/wms:Layer"
            
            # Tentar buscar usando o namespace WMS
            for layer_tag in root.findall(layers_xpath, namespaces):
                title_element = layer_tag.find("wms:Title", namespaces)
                name_element = layer_tag.find("wms:Name", namespaces)
                
                if name_element is not None and title_element is not None:
                    title = title_element.text
                    name = name_element.text
                    
                    if name and title:
                        # Formato: "Display Name (ASSINATURA_PA:layer_name)"
                        self.camadas.append(f"{title} ({name})")
            
            # Se não encontrou camadas, tentar buscar sem namespace (para maior compatibilidade)
            if not self.camadas:
                layers_xpath_no_ns = ".//Layer/Layer"
                for layer_tag in root.findall(layers_xpath_no_ns):
                    title_element = layer_tag.find("Title")
                    name_element = layer_tag.find("Name")
                    
                    if name_element is not None and title_element is not None:
                        title = title_element.text
                        name = name_element.text
                        
                        if name and title:
                            # Formato: "Display Name (ASSINATURA_PA:layer_name)"
                            self.camadas.append(f"{title} ({name})")
            
            if self.camadas:
                self.show_layer_list()
            else:
                QMessageBox.information(None, "Aviso", "Nenhuma camada disponível para o seu usuário.")
                
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                QMessageBox.critical(None, "Erro de Autenticação", 
                                   "Suas credenciais não são mais válidas. Por favor, faça login novamente.")
                self.is_authenticated = False
                self.auth_session = None
                self.show_login_dialog()
            else:
                QMessageBox.critical(None, "Erro de Conexão", 
                                   f"Erro ao carregar camadas: {e}")
        except Exception as e:
            QMessageBox.critical(None, "Erro", f"Erro inesperado ao carregar camadas: {e}")

    def show_layer_list(self):
        """Exibe o diálogo com a lista de camadas disponíveis"""
        self.current_layer_dialog = LayerListDialog(
            parent=self.iface.mainWindow(), 
            load_layers_callback=self.load_selected_layers,
            logout_callback=self.logout_user,
            user_name=self.usuario
        )
        
        # Preencher a lista de camadas
        self.current_layer_dialog.list_widget.addItems(self.camadas)
        
        # Atualizar o título do grupo com a contagem
        layers_group = self.current_layer_dialog.findChild(QGroupBox, "layers_group")
        if layers_group:
            layers_group.setTitle(f"Camadas Encontradas ({len(self.camadas)})")
            
        # Conectar o filtro de busca
        self.current_layer_dialog.search_box.textChanged.connect(self.filter_layer_list)
        
        # Conectar a seleção de itens para habilitar o botão
        self.current_layer_dialog.list_widget.itemSelectionChanged.connect(self.toggle_load_button)
        
        self.current_layer_dialog.exec_()

    def filter_layer_list(self, text):
        """Filtra a lista de camadas com base no texto digitado."""
        if not self.current_layer_dialog:
            return
            
        for i in range(self.current_layer_dialog.list_widget.count()):
            item = self.current_layer_dialog.list_widget.item(i)
            if text.lower() in item.text().lower():
                item.setHidden(False)
            else:
                item.setHidden(True)
                
        # Atualizar o botão de carregar
        self.toggle_load_button()

    def toggle_load_button(self):
        """Habilita/desabilita o botão de carregar com base na seleção."""
        if not self.current_layer_dialog:
            return
            
        selected_count = len(self.current_layer_dialog.list_widget.selectedItems())
        self.current_layer_dialog.btn_carregar.setEnabled(selected_count > 0)

    def load_selected_layers(self):
        """Carrega as camadas selecionadas em uma thread separada."""
        if not self.current_layer_dialog:
            return
            
        dlg = self.current_layer_dialog
        list_widget = dlg.list_widget
        btn_carregar = dlg.btn_carregar
        progress_frame = dlg.progress_frame
        progress_bar = dlg.progress_bar
        
        selected_items = list_widget.selectedItems()
        if not selected_items:
            return
            
        # Extrair nomes das camadas selecionadas
        selected_layers = []
        for item in selected_items:
            # Extrair o nome da camada do texto do item
            text = item.text()
            # Formato: "Display Name (ASSINATURA_PA:layer_name)"
            start = text.rfind("(") + 1
            end = text.rfind(")")
            layer_name = text[start:end]
            selected_layers.append(layer_name)
        
        # Mostrar progresso
        progress_frame.show()
        btn_carregar.setEnabled(False)
        progress_bar.setValue(0)
        
        # Iniciar worker thread
        self.worker = LayerLoadWorker(selected_layers, self.usuario, self.senha)
        self.worker.progress.connect(progress_bar.setValue)
        self.worker.finished.connect(lambda layers: self.on_layers_loaded(layers, dlg, progress_frame, btn_carregar))
        self.worker.error.connect(lambda msg: QMessageBox.warning(None, "Erro", msg))
        self.worker.start()

    def logout_user(self, dialog=None):
        """Realiza logout do usuário"""
        reply = QMessageBox.question(None, "Logout", 
                                   "Deseja fazer logout?\n\nIsso irá limpar suas credenciais salvas.",
                                   QMessageBox.Yes | QMessageBox.No, 
                                   QMessageBox.No)
        
        # Limpar estado de autenticação
        self.is_authenticated = False
        self.auth_session = None
        self.usuario = None
        self.senha = None
        self.camadas.clear()
        
        # Limpar credenciais salvas se confirmado
        if reply == QMessageBox.Yes:
            self.settings.remove("username")
            self.settings.remove("password")
        
        if dialog:
            dialog.reject()
            
        QMessageBox.information(None, "Logout", "Logout realizado com sucesso.")
    
    def on_layers_loaded(self, loaded_layers, dialog, progress_frame, button):
        """Callback quando as camadas terminam de carregar"""
        progress_frame.hide()
        button.setEnabled(True)
        
        if loaded_layers:
            QMessageBox.information(None, "Sucesso", 
                                  f"{len(loaded_layers)} camada(s) carregada(s) com sucesso!")
            dialog.accept()
        else:
            QMessageBox.warning(None, "Aviso", "Nenhuma camada foi carregada com sucesso.")
