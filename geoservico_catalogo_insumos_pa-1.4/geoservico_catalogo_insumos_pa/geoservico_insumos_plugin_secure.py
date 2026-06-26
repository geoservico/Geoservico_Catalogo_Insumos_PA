# -*- coding: utf-8 -*-
from qgis.PyQt.QtWidgets import (QAction, QMessageBox, QListWidget, QPushButton, 
                                 QVBoxLayout, QDialog, QLabel, QProgressBar, 
                                 QHBoxLayout, QFrame, QSpacerItem, QSizePolicy,
                                 QCheckBox, QLineEdit, QGroupBox, QDialogButtonBox)
from qgis.PyQt.QtGui import QIcon, QFont, QPixmap
from qgis.PyQt.QtCore import Qt, QThread, pyqtSignal, QSettings
from qgis.core import QgsProject, QgsRasterLayer, QgsMessageLog, Qgis, QgsDataSourceUri
from PyQt5 import uic
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

    def initGui(self):
        self.action = QAction(QIcon(os.path.join(self.plugin_dir, "icon.png")),
                              "Geoserviço - Insumos por Assinatura", self.iface.mainWindow())
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
        # Verificar se já está autenticado
        if self.is_user_authenticated() and self.validate_authentication():
            # Se já está autenticado, mostrar diretamente a lista de camadas
            if self.camadas:
                self.show_layer_list()
            else:
                # Recarregar camadas se necessário
                self.load_available_layers()
        else:
            # Mostrar diálogo de login
            self.show_login_dialog()

    def show_login_dialog(self):
        """Exibe o diálogo de login"""
        ui_path = os.path.join(self.plugin_dir, "form_login.ui")
        self.login_dialog = uic.loadUi(ui_path)
        
        # Carregar credenciais salvas (apenas usuário, senha não é salva por segurança)
        saved_user = self.settings.value("username", "")
        if saved_user:
            self.login_dialog.lineUser.setText(saved_user)
            self.login_dialog.saveCredentialsCheckBox.setChecked(True)

        # Informar ao usuário que a senha não será salva
        self.login_dialog.saveCredentialsCheckBox.setText("Lembrar usuário (senha não será salva por segurança)")

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

        if save_credentials:
            self.settings.setValue("username", self.usuario)
            # Senha não é salva por segurança
        else:
            self.settings.remove("username")
        
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

        # Tentar autenticar
        if self.authenticate_user():
            progress_dialog.close()
            self.login_dialog.accept()
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
            namespaces = {"wms": "http://www.opengis.net/wms"}
            self.camadas.clear()
            
            for layer in root.findall(".//wms:Layer/wms:Layer", namespaces):
                name_el = layer.find("wms:Name", namespaces)
                title_el = layer.find("wms:Title", namespaces)
                
                if name_el is not None:
                    layer_info = {
                        'name': name_el.text,
                        'title': title_el.text if title_el is not None else name_el.text
                    }
                    self.camadas.append(layer_info)
                    
            if self.camadas:
                self.show_layer_list()
            else:
                QMessageBox.information(None, "Informação", "Nenhuma camada encontrada no workspace ASSINATURA_PA.")
                
        except Exception as e:
            QMessageBox.critical(None, "Erro", f"Falha ao carregar camadas do servidor:\n{str(e)}")
            # Em caso de erro, limpar estado de autenticação
            self.is_authenticated = False
            self.auth_session = None

    def show_layer_list(self):
        """Exibe a lista de camadas (apenas se autenticado)"""
        if not self.is_user_authenticated():
            QMessageBox.warning(None, "Acesso Negado", 
                              "Você precisa estar logado para acessar as camadas.\n\nFaça login primeiro.")
            self.show_login_dialog()
            return

        dlg = QDialog()
        dlg.setWindowTitle("Camadas Disponíveis - Geoserviço")
        dlg.setFixedSize(600, 500)
        dlg.setStyleSheet("""
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
        
        main_layout = QVBoxLayout(dlg)
        
        # Header com logo e informações de usuário
        header_frame = QFrame()
        header_layout = QHBoxLayout(header_frame)
        
        # Logo
        logo_label = QLabel()
        pixmap = QPixmap(os.path.join(self.plugin_dir, "icon.png"))
        scaled_pixmap = pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo_label.setPixmap(scaled_pixmap)
        
        # Título e informações do usuário
        title_info_layout = QVBoxLayout()
        title_label = QLabel("Camadas Disponíveis")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        
        user_label = QLabel(f"Usuário: {self.usuario}")
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
        logout_button.clicked.connect(lambda: self.logout_user(dlg))
        
        header_layout.addWidget(logo_label)
        header_layout.addLayout(title_info_layout)
        header_layout.addStretch()
        header_layout.addWidget(logout_button)
        
        main_layout.addWidget(header_frame)
        
        # Filtro de busca
        search_group = QGroupBox("Filtrar Camadas")
        search_layout = QVBoxLayout(search_group)
        
        search_box = QLineEdit()
        search_box.setPlaceholderText("Digite para filtrar camadas...")
        search_layout.addWidget(search_box)
        
        main_layout.addWidget(search_group)
        
        # Lista de camadas
        layers_group = QGroupBox(f"Camadas Encontradas ({len(self.camadas)})")
        layers_layout = QVBoxLayout(layers_group)
        
        list_widget = QListWidget()
        list_widget.setSelectionMode(QListWidget.MultiSelection)
        
        # Adicionar camadas com títulos mais amigáveis
        for layer_info in self.camadas:
            display_name = layer_info['title'].replace("ASSINATURA_PA:", "")
            list_widget.addItem(f"{display_name} ({layer_info['name']})")
        
        layers_layout.addWidget(list_widget)
        main_layout.addWidget(layers_group)
        
        # Controles
        controls_layout = QHBoxLayout()
        
        select_all_cb = QCheckBox("Selecionar Todas")
        controls_layout.addWidget(select_all_cb)
        controls_layout.addStretch()
        
        btn_carregar = QPushButton("Carregar Selecionadas")
        btn_carregar.setEnabled(False)
        controls_layout.addWidget(btn_carregar)
        
        main_layout.addLayout(controls_layout)
        
        # Barra de progresso (inicialmente oculta)
        progress_frame = QFrame()
        progress_layout = QVBoxLayout(progress_frame)
        progress_label = QLabel("Carregando camadas...")
        progress_bar = QProgressBar()
        progress_layout.addWidget(progress_label)
        progress_layout.addWidget(progress_bar)
        progress_frame.hide()
        
        main_layout.addWidget(progress_frame)
        
        # Conectar eventos
        def on_selection_changed():
            selected_count = len(list_widget.selectedItems())
            btn_carregar.setEnabled(selected_count > 0)
            btn_carregar.setText(f"Carregar Selecionadas ({selected_count})")
        
        def on_select_all_changed(checked):
            if checked:
                list_widget.selectAll()
            else:
                list_widget.clearSelection()
        
        def filter_layers(text):
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                item.setHidden(text.lower() not in item.text().lower())
        
        def load_selected_layers():
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
        
        list_widget.itemSelectionChanged.connect(on_selection_changed)
        select_all_cb.toggled.connect(on_select_all_changed)
        search_box.textChanged.connect(filter_layers)
        btn_carregar.clicked.connect(load_selected_layers)
        
        dlg.exec_()

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

