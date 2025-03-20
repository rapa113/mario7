
try:
    from PySide6.QtWidgets import QMainWindow, QApplication, QMenu
    from PySide6.QtWidgets import QVBoxLayout,QTableWidgetItem, QLabel
    from PySide6.QtWidgets import QWidget, QListWidgetItem, QTreeWidgetItem
    from PySide6.QtUiTools import QUiLoader
    from PySide6.QtCore import Qt, QFile, QSize, QObject
    from PySide6.QtGui import QIcon, QColor, QFontMetrics 
    from PySide6.QtGui import QStandardItemModel, QStandardItem, QPixmap

    
except:
    from PySide2.QtWidgets import QMainWindow, QApplication, QMenu
    from PySide2.QtWidgets import QVBoxLayout, QTableWidgetItem, QLabel
    from PySide2.QtWidgets import QWidget, QListWidgetItem, QTreeWidgetItem
    from PySide2.QtUiTools import QUiLoader
    from PySide2.QtCore import Qt, QFile, QSize, QObject
    from PySide2.QtGui import QIcon, QColor, QFontMetrics 
    from PySide2.QtGui import QStandardItemModel, QStandardItem, QPixmap
    import maya.cmds as cmds
    import shutil

import os
import json
from shotgun_api3 import Shotgun
import sg_api

class MainCtrl(QMainWindow):
    def __init__(self):
        super().__init__()
        self.root_path = "/nas/Batz_Maru"

        json_path = "/nas/Batz_Maru/pingu/nana/merge/user_info.json"
        with open(json_path,'r', encoding='utf-8') as f:
            user_info = json.load(f)
            user_id = user_info['id']

        project_name = "Jupiter"
        self.path_manager = sg_api.MyTask(user_id, project=project_name)
        folders = self.path_manager.display_folders()

        self.load_ui()
        self.center_window()

        self.UISetup = UISetup(self.ui)
        self.UtilityMgr = UtilityMgr(self.ui, self.ui.treeWidget)
        self.TreeMgr = TreeMgr(self.ui.treeWidget, self.ui.treeWidget_task, folders, self.root_path, self.UtilityMgr, self.ui)
        self.TableMgr = TableMgr(self.ui, self.ui.treeWidget, self.ui.treeWidget_task, self.ui.tableWidget, self.ui.label_path, folders, self.root_path)
        self.MayaMgr = MayaMgr(self.TableMgr)
        self.ButtonMgr = ButtonMgr(self.ui, self.TableMgr, self.TreeMgr, self.root_path, self.UISetup, self.MayaMgr)  
        self.ShotGridMgr = ShotGridMgr(self.path_manager)
        self.SubUISetup = SubUISetup(self.ui, self.TableMgr, self.ui.label_path, self.path_manager, self.ShotGridMgr)

        self.ui.installEventFilter(self)

    def center_window(self):
        """ UI 화면 중앙 배치 """
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        ui_geometry = self.ui.frameGeometry()
        center_point = screen_geometry.center()

        ui_geometry.moveCenter(center_point)
        self.ui.move(ui_geometry.topLeft())

    def eventFilter(self, obj, event):
        """크기 변경 시 TableMgr의 resize_window 실행"""
        if obj == self.ui and event.type() == event.Resize:
            self.TableMgr.resize_window()
        return super().eventFilter(obj, event)

    def load_ui(self):
        ui_file_path = "/nas/Batz_Maru/pingu/nana/03_14/kec/kec_loaderUI_0313.ui"
        ui_file = QFile(ui_file_path)
        loader = QUiLoader()
        self.ui = loader.load(ui_file)
        self.ui.show()
        ui_file.close()

class ShotGridMgr:
    def __init__(self, path_manager):
        self.path_manager = path_manager

    def set_task_name(self, task_name):
        self.current_task = task_name
        self.load_tasks()

    def load_tasks(self):
        tasks = self.path_manager.get_tasks()

        task_dict = {}
        for task in tasks:
            entity_name = task["entity"]["name"]
            step_name = task["step"]["name"]
            entity_type = task["entity"]["type"]
            days = int(task['duration'] / 60 / 8)
            task_name = f"{entity_name}_{step_name}" if entity_type == "Shot" else f"{entity_name}_{task['content']}_{step_name}"
           
            task_dict[task_name] = {
                "start_date": task["start_date"],
                "due_date": task["due_date"],
                "duration": days,
                "entity_type": entity_type,
                "description": task.get("sg_description", "N/A"),
            }

        self.task_dict = task_dict  # 저장해서 이후 검색 가능
        self.pull_task_info(self.current_task)
        print(f"테스크 분류 결과: {self.task_dict}")

    def pull_task_info(self, current_task):
        matched_task = self.task_dict.get(current_task)
        if matched_task:
            return [
                f"Sta_Date : {matched_task['start_date']}",
                f"Due_Date : {matched_task['due_date']}",
                f"Duration : {matched_task['duration']} days",
                f"Description : {matched_task['description']}",
            ]
        return []

class MayaMgr:
    def __init__(self, table_mgr):
        self.table_mgr = table_mgr

        self.table_mgr.tableWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_mgr.tableWidget.customContextMenuRequested.connect(self.show_menu)
    
    def show_menu(self, position):

        # 테이블위젯 좌표값
        item = self.table_mgr.tableWidget.itemAt(position)
        self.selected_item = item.text()
        
        menu = QMenu()

        open_action = menu.addAction("Open")
        import_action = menu.addAction("Import")
        reference_action = menu.addAction("Reference")

        # QAction이 실행되었을 때 실행할 함수 연결
        open_action.triggered.connect(self.maya_open)
        import_action.triggered.connect(self.maya_import)
        reference_action.triggered.connect(self.maya_reference)

        menu.exec_(self.table_mgr.tableWidget.viewport().mapToGlobal(position))

    def maya_open(self):
        file_path = os.path.join(self.table_mgr.current_folder, self.selected_item)

        if os.path.exists(file_path):
            file_extension = os.path.splitext(file_path)[-1].lower()
            file_type = "mayaAscii" if file_extension == ".ma" else "mayaBinary"

            print(f"Import 실행: {file_path}")
            cmds.file(file_path, open=True, force=True, type=file_type, ignoreVersion=True, options="v=0;")


    def maya_import(self):
        file_path = os.path.join(self.table_mgr.current_folder, self.selected_item)

        if os.path.exists(file_path):
            file_extension = os.path.splitext(file_path)[-1].lower()
            file_type = "mayaAscii" if file_extension == ".ma" else "mayaBinary"

            print(f"Import 실행: {file_path}")
            cmds.file(file_path, i=True, type=file_type, ignoreVersion=True, ra=True, mergeNamespacesOnClash=False, options="v=0;", pr=True, importFrameRate=True)

    def maya_reference(self):
        file_path = os.path.join(self.table_mgr.current_folder, self.selected_item)

        if not os.path.exists(file_path):
            print(f"파일을 찾을 수 없습니다: {file_path}")
            return

        file_extension = os.path.splitext(file_path)[-1].lower()
        file_type = "mayaAscii" if file_extension == ".ma" else "mayaBinary"
        namespace = os.path.splitext(self.selected_item)[0]  # 파일명 기반 네임스페이스
        cmds.file(file_path, reference=True, type=file_type, ignoreVersion=True, mergeNamespacesOnClash=False, options="v=0;", pr=True, namespace=namespace, force=True)

  
class SubUISetup:
    def __init__(self, ui, table_mgr, label_path, path_manager, shotgrid_mgr):
        self.ui = ui
        self.table_mgr = table_mgr
        self.label_path = label_path 
        self.path_manager = path_manager
        self.shotgrid_mgr = shotgrid_mgr

        self.ui.treeWidget.itemClicked.connect(self.listWidget_info)
        self.ui.tableWidget.cellClicked.connect(self.tableWidget_info)
        self.ui.treeWidget_task.itemClicked.connect(self.listWidget_task_info)

    def tableWidget_info(self, row, column):
        sub_list_info = []

        # 파일명
        item = self.ui.tableWidget.item(row, column)
        file_name = item.text().strip()
        sub_list_info.append(f"Name : {file_name}")

        # 경로
        path_name = self.label_path.text().strip()
        project_name = path_name.split("/")[3]  
        sub_list_info.append(f"Project : {project_name}")  

        self.listWidget_sub(sub_list_info)

    def listWidget_task_info(self, item):
        
        sub_list_info = []
        
        file_name = item.text(0)

        sub_list_info.append(f"Name : {file_name}")
        self.shotgrid_mgr.set_task_name(file_name)
        result = self.shotgrid_mgr.pull_task_info(file_name)
        sub_list_info.extend(result)

        self.listWidget_sub(sub_list_info)

    def listWidget_info(self, item):
        
        sub_list_info = []
        
        file_name = item.text(0)
        sub_list_info.append(f"Name : {file_name}")
        self.listWidget_sub(sub_list_info)

    def listWidget_sub(self, list_info):
        self.ui.listWidget_sub.clear()
        
        for info in list_info:
            item = QListWidgetItem(info) 
            item.setToolTip(info) 
            self.ui.listWidget_sub.addItem(item)

class TreeMgr:
    def __init__(self, tree_widget, tree_Widget_task, folders, root_path, utility_mgr, ui):

        self.tree_widget = tree_widget
        self.tree_Widget_task = tree_Widget_task
        self.folders = folders
        self.root_path = root_path
        self.utility_mgr = utility_mgr 
        self.ui = ui

        self.show_file()

    def show_file(self):
        self.tree_widget.setHeaderLabels(["Batz_Maru"])
        self.tree_Widget_task.setHeaderLabels(["Task"])

        folder_structure = self.get_folder(self.root_path)
        folder_structure_task = self.get_task()

        self.populate_tree(folder_structure, self.tree_widget)
        self.populate_tree(folder_structure_task, self.tree_Widget_task)

    def get_folder(self, path=None):

        if path is None:
            path = self.root_path
        
        folder_dict = {}
        
        if os.path.isdir(path):
            for item in os.listdir(path):
                full_path = os.path.join(path, item)
                if os.path.isdir(full_path):
                    folder_dict[item] = self.get_folder(full_path)
                    
        return folder_dict
    
    def get_task(self, task_paths=None):
        folder_dict_task = {}

        if task_paths is None:
            task_paths = self.folders

        for task_path in task_paths:  
            if os.path.isdir(task_path):  
                sub_folders = [] 

                for item in os.listdir(task_path):
                    full_path = os.path.join(task_path, item)

                    if os.path.isdir(full_path): 
                        sub_folders.append(full_path)  

                folder_name = os.path.basename(task_path) 
                folder_dict_task[folder_name] = {}  

                for sub_folder in sub_folders:
                    sub_folder_name = os.path.basename(sub_folder)
                    folder_dict_task[folder_name][sub_folder_name] = {}  

        return folder_dict_task

    def populate_tree(self, folder_dict, parent_item):
        """ 주어진 폴더 딕셔너리를 QTreeWidget에 추가하는 함수 """

        for folder, sub_folders in folder_dict.items():
            child_item = QTreeWidgetItem(parent_item)
            child_item.setText(0, folder)

            self.populate_tree(sub_folders, child_item)

class ButtonMgr:
    def __init__(self, ui, tablemgr, tree_mgr, root_path, ui_setup, maya_mgr):
        self.ui = ui
        self.table_mgr = tablemgr
        self.tree_mgr = tree_mgr
        self.root_path = root_path 
        self.ui_setup = ui_setup 
        self.maya_mgr = maya_mgr


        self.history = [] 
        self.current_index = -1  

        self.ui.pushButton_home.clicked.connect(self.go_home)
        self.ui.pushButton_back.clicked.connect(self.go_back)
        self.ui.pushButton_front.clicked.connect(self.go_front)

        self.ui.treeWidget.itemClicked.connect(self.click_history)
        self.ui.comboBox_task.currentIndexChanged.connect(self.new_combo) 

        self.ui.pushButton_list_menu.clicked.connect(self.view_list)
        self.ui.pushButton_icon_menu.clicked.connect(self.view_icon)
        
        # listView_button 우클릭
        self.ui.listView_button.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.listView_button.customContextMenuRequested.connect(self.show_menu)

    def show_menu(self, position):
        item = self.table_mgr.tableWidget.itemAt(position)
    
        self.selected_item = item.text()
        menu = QMenu()
        open_action = menu.addAction("Open")
        menu.addAction("Import")
        menu.addAction("Reference")

        open_action.triggered.connect(self.maya_mgr.maya_open)

        menu.exec_(self.table_mgr.tableWidget.viewport().mapToGlobal(position))

    def view_icon(self):
        """아이콘 뷰 활성화"""
        self.ui.listView_button.hide() 
        self.ui.tableWidget.show() 

    def view_list(self):
        """리스트 뷰 활성화"""
        current_item = self.ui.treeWidget.currentItem()
        task_item = self.ui.treeWidget_task.currentItem()

        if not current_item and not task_item:
            return

        if current_item:
            self.current_folder = self.table_mgr.get_full_path(current_item)

        elif task_item:
            self.current_folder = self.table_mgr.get_task_path(task_item)

        if not os.path.exists(self.current_folder):
            print(f"경로가 존재하지 않음: {self.current_folder}")
            return

        # 리스트뷰 활성화
        self.ui.tableWidget.hide()
        self.ui.listView_button.show()

        # 테이블과 동일한 크기 적용
        self.ui.listView_button.setGeometry(self.ui.tableWidget.geometry())

        # 모델 설정
        model = QStandardItemModel()
        self.ui.listView_button.setModel(model)

        for file in os.listdir(self.current_folder):
            model.appendRow(QStandardItem(file))

    def new_combo(self):
        self.ui.treeWidget_task.clear()
        project_name = self.ui.comboBox_task.currentText()

        self.path_manager = sg_api.MyTask(user_id=133, project=project_name)
        folders = self.path_manager.display_folders()
        self.update_task_tree(folders)

    def update_task_tree(self, folders):
        """Task 트리를 새로운 값으로 업데이트"""
        task_data = self.tree_mgr.get_task(folders) 
        self.tree_mgr.populate_tree(task_data, self.ui.treeWidget_task) 


    def click_history(self, item):
        """트리에서 선택한 항목 기록"""
        if self.current_index < len(self.history) - 1:
            self.history = self.history[:self.current_index + 1] 

        self.history.append(item)  
        self.current_index += 1 

        full_path = self.table_mgr.get_full_path(item)
        self.ui.label_path.setText(full_path)

    def go_back(self):
        """뒤로 가기 버튼 동작 - 이전 트리 항목 선택"""
        if self.current_index > 0:
            self.current_index -= 1
            item = self.history[self.current_index]  

            self.ui.tableWidget.clearContents()
            self.ui.tableWidget.setRowCount(0)
            self.ui.tableWidget.setColumnCount(0)

            self.ui.treeWidget.setCurrentItem(item) 
            self.ui.treeWidget.scrollToItem(item)  
            print(f" 뒤로 가기: {item.text(0)}")

            folder_path = self.table_mgr.get_full_path(item)

            if os.path.isdir(folder_path):  
                print(f"테이블 업데이트: {folder_path}")
                self.table_mgr.display_files(os.listdir(folder_path), folder_path)  # 테이블 갱신
            else:
                print(f"폴더가 존재하지 않습니다: {folder_path}")

    def go_front(self):
        """앞으로 가기 버튼 동작"""
        if self.current_index < len(self.history) - 1:
            self.current_index += 1
            item = self.history[self.current_index] 

            self.ui.tableWidget.clearContents()
            self.ui.tableWidget.setRowCount(0)
            self.ui.tableWidget.setColumnCount(0)

            self.ui.treeWidget.setCurrentItem(item) 
            self.ui.treeWidget.scrollToItem(item)  

            folder_path = self.table_mgr.get_full_path(item) 

            if os.path.isdir(folder_path): 
                print(f"테이블 업데이트: {folder_path}")
                self.table_mgr.display_files(os.listdir(folder_path), folder_path) 
            else:
                print(f"폴더가 존재하지 않습니다: {folder_path}")


    def go_home(self):
        """홈 버튼 클릭 시 초기화"""
        self.history = [] 
        self.current_index = -1
        
        self.ui.treeWidget.clearSelection() 
        self.ui.treeWidget_task.clearSelection()
        self.ui.tableWidget.clear()
        self.tree_mgr.show_file(self.root_path) 
        
        folder_path = self.root_path 

        if os.path.isdir(folder_path):
            self.ui.tableWidget.clearContents()
            self.ui.tableWidget.setRowCount(0)
            self.ui.tableWidget.setColumnCount(0)
            self.table_mgr.display_files(os.listdir(folder_path), folder_path)
        
        self.ui.treeWidget.itemClicked.connect(self.click_history)
        
class UtilityMgr:
    """트리 위젯 버튼 구현 클래스"""
    def __init__(self,  ui, tree_widget):
        self.ui = ui
        self.tree_widget = tree_widget
        self.root_path = "/nas/Batz_Maru"

        # ComboBox_task_pro
        self.ui.comboBox_task.addItems(self.get_projects())
        self.ui.comboBox_task.currentIndexChanged.connect(self.print_selected_project) 

        # Enter 키 입력시 실행
        self.ui.lineEdit.returnPressed.connect(self.run_search)

        # tableWidget/슬라이더 - 스타일 및 기능 추가
        self.ui.horizontalSlider.valueChanged.connect(self.update_asset_icons)

        # tableWidget/슬라이더 - 기본값 설정
        self.ui.horizontalSlider.setValue(50)
        
    def print_selected_project(self):
        selected_project = self.ui.comboBox_task.currentText()
        print(f"선택된 프로젝트: {selected_project}")

    def get_projects(self):
        project = []
        for name in os.listdir(self.root_path):
            project_path = f"{self.root_path}/{name}" # 경로 만들기
            if not os.path.isdir(project_path): # 디렉토리가 아니면 패스
                continue
            project.append(name)
        return project

    # 검색 실행 함수
    def run_search(self): 
        """ 검색 실행 함수 - 트리 위젯에서 검색 """
        keyword = self.ui.lineEdit.text().strip() 

        if not keyword:  
            print("검색어를 입력하세요.")
            return

        found = self.find_and_select_in_tree(keyword)
        
        if not found:
            print(f"'{keyword}'에 해당하는 폴더 또는 파일을 찾을 수 없습니다.")
        else:
            print(f"'{keyword}' 검색 결과를 강조 표시합니다.")

    def find_and_select_in_tree(self, keyword):
        """ 트리에서 키워드와 일치하는 항목을 찾아 선택 """

        def search_items(item):
            """ 재귀적으로 트리를 탐색하면서 키워드 검색 """
            for i in range(item.childCount()):
                child = item.child(i) 
                
                if keyword.lower() in child.text(0).lower():  
                    self.tree_widget.setCurrentItem(child)  
                    self.tree_widget.scrollToItem(child)  
                    return True 
                
                if search_items(child):
                    item.setExpanded(True) 
                    return True  
        
            return False  
        
        for i in range(self.tree_widget.topLevelItemCount()):
            top_item = self.tree_widget.topLevelItem(i) 
            if search_items(top_item):
                return True  
        
        return False 

    def update_asset_icons(self):
        zoom_value = self.ui.horizontalSlider.value()
        icon_size = 50 + (zoom_value / 100) * 100  

        row_count = self.ui.tableWidget.rowCount()
        col_count = self.ui.tableWidget.columnCount()

        for row in range(row_count):
            for col in range(col_count):
                widget = self.ui.tableWidget.cellWidget(row, col)
                if widget:
                    layout = widget.layout()
                    if layout and layout.count() > 1:
                        image_label = layout.itemAt(0).widget()
                        if isinstance(image_label, QLabel):
                            thumb_path = "/nas/Batz_Maru/pingu/imim/batzz_1.png"
                            pixmap = QPixmap(thumb_path).scaled(
                                int(icon_size), int(icon_size),
                                Qt.KeepAspectRatio, Qt.SmoothTransformation
                            )
                            image_label.setPixmap(pixmap)
                            image_label.setScaledContents(True)
                            image_label.setFixedSize(int(icon_size), int(icon_size))

        self.ui.tableWidget.verticalHeader().setDefaultSectionSize(int(icon_size) + 30)  
        self.ui.tableWidget.horizontalHeader().setDefaultSectionSize(int(icon_size) + 30)

        self.ui.tableWidget.update()
        self.ui.tableWidget.viewport().update()
        
    def refresh_table(self):
        current_item = self.ui.treeWidget.currentItem()
        if current_item:
            folder_path = self.asset_manager.get_full_path(current_item)
            if os.path.isdir(folder_path):
                self.asset_manager.display_files(os.listdir(folder_path))
                self.update_asset_icons()

class TableMgr:
    def __init__(self, ui, tree_widget, treeWidget_task, table_widget, label_path, folders, root_path):
        self.ui = ui
        self.treeWidget = tree_widget
        self.treeWidget_task = treeWidget_task
        self.tableWidget = table_widget
        self.root_path = root_path
        self.label_path = label_path
        self.folders = folders
        
        self.treeWidget.itemClicked.connect(self.get_asset)
        self.treeWidget_task.itemClicked.connect(self.get_task_assets)
        self.tableWidget.cellDoubleClicked.connect(self.open_item)

        

    def get_asset(self, item):
        """선택한 폴더의 파일 목록을 테이블에 표시"""
        folder_path = self.get_full_path(item) 
        self.display_files(os.listdir(folder_path), folder_path)
        
        # 분리 예정
        self.label_path.setText(folder_path)

    def get_task_assets(self, item):
        task_path = self.get_task_path(item)
        self.display_files(os.listdir(task_path), task_path)
        
        # 분리 예정
        self.label_path.setText(task_path)

    def get_full_path(self, item):
        """ full 트리에서 경로 추출"""

        path_list = []

        while item:
            path_list.insert(0, item.text(0)) 
            item = item.parent()

        full_path = os.path.join(self.root_path, *path_list)
        
        return full_path

    def get_task_path(self, task_item):
        """ task 트리에서 경로 추출 """
        
        task_list = []

        while task_item:
            if isinstance(task_item, QTreeWidgetItem):
                task_list.insert(0, task_item.text(0)) 
                task_item = task_item.parent()
            
            elif isinstance(task_item, QTableWidgetItem):
                task_list.insert(0, task_item.text()) 
                break  
            
            else:
                print(f"알 수 없는 아이템 타입: {type(task_item)}") 
                break
        
        relative_path = os.path.join(*task_list)
        print(f"클릭 경로: {relative_path}")

        base_path = None
        for folder in self.folders:
            print (f"샷건파일확인{folder}")
            if relative_path.startswith(os.path.basename(folder)):  # 폴더명이 포함된 최상위 경로 찾기
                base_path = folder
                break
        if base_path is None:
            return relative_path  
        
        full_path = os.path.join(base_path, relative_path.replace(os.path.basename(base_path), "").lstrip("/"))
        return full_path

    def resize_window(self):
        new_width = self.ui.width()
        new_height = self.ui.height()

        self.ui.tableWidget.setGeometry(280, 110, new_width - 300, new_height - 200)
        
        self.ui.tableWidget.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.ui.tableWidget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)  

        
        if hasattr(self, "current_folder") and self.current_folder:
            self.display_files(os.listdir(self.current_folder), self.current_folder)

    def display_files(self, file_list, folder_path):
        """테이블 위젯에 파일 목록을 표시"""
        self.tableWidget.clearContents() 
        self.current_folder = folder_path

        column_width = 100  
        table_width = self.tableWidget.width() 
        
        column_count = max(0, table_width // column_width)  
        row_count = (len(file_list) + column_count - 1) // column_count  

        print(f"테이블 업데이트: {table_width}px → {column_count}열, {row_count}행")

        self.tableWidget.setColumnCount(column_count)
        self.tableWidget.setRowCount(row_count)
        self.tableWidget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  
        
 

        for index, file in enumerate(file_list):
            row = index // column_count  
            col = index % column_count   
            self.make_asset_table(row, col, file, folder_path)  

    def make_asset_table(self, row, col, file, folder_path):
        """테이블에 개별 애셋(파일)을 추가"""
        widget = QWidget()
        layout = QVBoxLayout()

        image_label = QLabel() 
        text_label = QLabel()  

        full_path = os.path.join(folder_path, file) 
        if os.path.isdir(full_path):
            thumb_path = "/nas/Batz_Maru/pingu/imim/batzz.png"
        else:
            thumb_path = "/nas/Batz_Maru/pingu/imim/batzz_mamb.png"

        pixmap = QPixmap(thumb_path).scaled(70, 70, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        image_label.setPixmap(pixmap)

        fm = QFontMetrics(text_label.font())
        max_width = 90 
        max_lines = 2
        elided_text = fm.elidedText(file, Qt.ElideRight, max_width) 
        text_label.setText(elided_text)

        layout.addWidget(image_label)
        layout.addWidget(text_label)
        widget.setLayout(layout)

        file_item = QTableWidgetItem(file)
        file_item.setForeground(QColor(255, 255, 255, 0)) 
        self.tableWidget.setItem(row, col, file_item)

        self.tableWidget.setCellWidget(row, col, widget)  


        self.tableWidget.setShowGrid(False) 
        self.tableWidget.horizontalHeader().setVisible(False)
        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.horizontalHeader().setDefaultSectionSize(100) 
        self.tableWidget.verticalHeader().setDefaultSectionSize(120) 
        self.tableWidget.verticalHeader().setMinimumSectionSize(30)

    def open_item(self, row, column):
        """더블 클릭 시 폴더 내부로 이동 또는 파일 실행"""
        item = self.tableWidget.item(row, column)
        if item is None:
            print("선택한 셀이 비어 있음!")
            return

        file_name = item.text().strip()
        full_path = os.path.join(self.current_folder, file_name)  

        if os.path.isdir(full_path):

            self.current_folder = full_path  
            self.display_files(os.listdir(full_path), full_path)  
            self.sync_tree_with_table(full_path)  


        else:
            print(f"파일 실행: {full_path}")
            self.open_maya_file(row, column)

    def sync_tree_with_table(self, folder_path):
        """테이블에서 폴더를 열면 트리도 해당 위치로 이동"""
        def find_item_by_path(item, target_path):
            """트리에서 특정 경로를 가진 아이템을 찾는 재귀 함수"""
            if self.get_full_path(item) == target_path:
                return item
            
            for i in range(item.childCount()):
                found_item = find_item_by_path(item.child(i), target_path)
                if found_item:
                    return found_item
            return None

        # 트리의 최상위부터 탐색
        for i in range(self.treeWidget.topLevelItemCount()):
            root_item = self.treeWidget.topLevelItem(i)
            target_item = find_item_by_path(root_item, folder_path)
            if target_item:
                self.treeWidget.setCurrentItem(target_item)  # 트리 위치 이동
                target_item.setExpanded(True)  # 폴더 자동 확장
                break

    def open_maya_file(self, row, column):
        """더블 클릭한 테이블의 파일을 Maya에서 실행"""

        item = self.tableWidget.item(row, column) 
        if item is None:
            print("선택한 셀이 비어 있음! 파일이 존재하지 않음.")
            print(f"현재 테이블 행 수: {self.tableWidget.rowCount()}")
            print(f"현재 테이블 열 수: {self.tableWidget.columnCount()}")
            return

        file_name = item.text() 
        folder_item = self.find_file_path_in_tree(file_name) 

        if folder_item is None:
            print(f"트리에서 파일 {file_name} 이(가) 포함된 폴더를 찾을 수 없음.")
            return

        file_folder = self.get_full_path(folder_item)  
        file_path = os.path.join(file_folder, file_name)

        print(f"최종 파일 경로: {file_path}")

        if os.path.exists(file_path):  
            if file_name.endswith((".ma", ".mb", ".fbx", ".obj")):  
                print(f"Maya 파일 실행: {file_path}")

                if cmds.file(file_path, q=True, exists=True):
                    cmds.file(new=True, force=True) 
                    cmds.file(file_path, open=True, force=True) 
                    print(f"{file_path} 실행 완료!")
                else:
                    print(f" 파일을 찾을 수 없습니다: {file_path}")
            else:
                print(f" 이 파일은 마야 파일이 아닙니다: {file_name}")
        else:
            print(f" 실제 파일이 존재하지 않음: {file_path}")

    def find_file_path_in_tree(self, file_name):
        """트리에서 해당 파일이 포함된 폴더를 찾아 반환"""
        def search_tree(item):
            for i in range(item.childCount()):
                child = item.child(i)
                folder_path = self.get_full_path(child)

                if os.path.exists(os.path.join(folder_path, file_name)):
                    return child

                # 하위 폴더 탐색
                found_item = search_tree(child)
                if found_item:
                    return found_item

            return None

        # 최상위 폴더부터 탐색 시작
        for i in range(self.treeWidget.topLevelItemCount()):
            top_item = self.treeWidget.topLevelItem(i)
            found_item = search_tree(top_item)
            if found_item:
                return found_item

        return None 
    
class UISetup(QObject):
    def __init__(self, ui):
        super().__init__() 
        self.ui = ui
        self.button_images = self.get_button_images()
        self.button_mapping = self.get_button_mapping()
        self.setup_button_styles()
        self.resize_window()
        self.set_background()
        self.apply_styles()
        self.image_path()

        self.ui.installEventFilter(self)

    def image_path(self):
        task_image = "/nas/Batz_Maru/pingu/imim/batzz_open.png"
        pixmap = QPixmap(task_image).scaled(200, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.ui.pushButton_luck.setIcon(QIcon(pixmap))
        self.ui.pushButton_luck.setIconSize(QSize(200, 180))
        self.ui.pushButton_luck.setFixedSize(200, 180)


    def eventFilter(self, obj, event):
        """창 크기 변경 감지"""
        if obj == self.ui and event.type() == event.Resize:         
            self.resize_window()
        return super().eventFilter(obj, event)

    def resize_window(self):
        """크기에 맞춰 tableWidget 크기 조정"""
        margin = 20  
        window_width = self.ui.width()
        window_height = self.ui.height()
        tab_width = self.ui.tabWidget.width() + 10
        new_width = self.ui.width()
        new_height = self.ui.height() 

        self.ui.pushButton_icon_menu.setGeometry(new_width - 310, 60, 40, 40)
        self.ui.pushButton_list_menu.setGeometry(new_width - 260, 60, 40, 40)
        self.ui.tableWidget.setGeometry(280, 110, new_width - 500, new_height - 200)
        self.ui.lineEdit.setGeometry(10, new_height - 115, 261, 28)
        self.ui.tabWidget.setGeometry(10, 110, 261, new_height - 230)
        self.ui.treeWidget.setGeometry(0, 0, 257, new_height - 267)
        self.ui.treeWidget_task.setGeometry(0, 0, 261, new_height - 230)
        self.ui.horizontalSlider.setGeometry(new_width -465, new_height - 72 , 240, 16)
        self.ui.pushButton_luck.setGeometry(new_width - 210, 10, 200, 180)
        self.ui.listWidget_sub.setGeometry(new_width - 210, 200, 200, new_height - 290)
  
    def set_background(self):
        """전체 UI의 배경을 설정"""
        self.ui.setStyleSheet("QMainWindow { background-color: black; }")

    # 버튼 스타일 적용 함수
    def setup_button_styles(self):
        """버튼 스타일 설정"""
        for button, key in self.button_mapping.items():
            normal_img, clicked_img = self.button_images[key]
            button.setStyleSheet(f"""
                QPushButton {{
                    border: none;
                    background: transparent;
                    background-image: url({normal_img});
                    background-repeat: no-repeat;
                    background-position: center;
                
                }}
                QPushButton:pressed {{
                    background-image: url({clicked_img});
                }}
            """)

    def get_button_images(self):
        """버튼에 사용될 이미지 경로 반환"""
        base_path = "/nas/Batz_Maru/pingu/imim"
        return {
            "home": (f"{base_path}/white/home.png", f"{base_path}/yellow/home_1.png"),
            "back": (f"{base_path}/white/ctrlz.png", f"{base_path}/yellow/ctrlz_1.png"),
            "front": (f"{base_path}/white/ctrlshiftz.png", f"{base_path}/yellow/ctrlshiftz_1.png"),
            "list_menu": (f"{base_path}/white/menu.png", f"{base_path}/yellow/menu_1.png"),
            "icon_menu": (f"{base_path}/white/icon_menu.png", f"{base_path}/yellow/icon_menu_1.png"),
            }

    def get_button_mapping(self):
        """버튼과 이미지 키 매핑"""
        return {
            self.ui.pushButton_home: "home",
            self.ui.pushButton_back: "back",
            self.ui.pushButton_front: "front",
            self.ui.pushButton_list_menu: "list_menu",
            self.ui.pushButton_icon_menu: "icon_menu",
        }

    def apply_styles(self):
        """UI 스타일을 설정하는 함수"""

        self.ui.listView_button.setStyleSheet("""
            QListView {
                background-color: #FFF8DC; /* 크림색 배경 */
                border: 2px solid #fdcb01; /* 배츠마루 테마 노랑 테두리 */
                color: #555555;
                font: 14px "Comic Sans MS";
                selection-background-color: #faefc1; /* 선택된 항목 배경 */
                padding: 5px;
            }
            QListView::item {
                padding: 5px;
            }
            QListView::item:selected {
                background-color: #faefc1;
                color: #000000;
                font-weight: bold;
            }
        """)

        self.ui.lineEdit.setStyleSheet("""
            QLineEdit {
                border: 0px solid #FFF8DC;
                border-radius: 10px;
                padding: 5px;
                font-size: 16px;
                background-color: #feeca4;
                color: #333333;
            }
            QLineEdit:focus {
                border: 2px solid #fdcb01;
                background-color: #FFF8DC;
            }
        """)

        self.ui.pushButton_luck.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
            }
        """)

        self.ui.treeWidget.setStyleSheet("""
        QTreeWidget {
            background-color: #FFF8DC; /* 크림색 배경 */
            border: 2px solid #fdcb01; /* 배츠마루 느낌의 노랑 테두리 */
            border-radius: 0px;
            color: #555555;
            font: 14px "Comic Sans MS"; /* 귀여운 느낌의 폰트 */
        }

        /* 헤더 스타일 */
        QHeaderView::section {
            background-color: #feeca4; /* 배츠마루 테마 연한 노랑 */
            color: #222222;
            font: bold 16px "Comic Sans MS"; /* 심플한 귀여운 느낌 */
            padding: 8px;
            border-radius: 8px;
            text-align: center;
        }

        /* 트리 아이템 스타일 */
        QTreeWidget::item {
            height: 32px;
            padding: 6px;
            border-radius: 2px;
        }

        QTreeWidget::item:selected {
            background-color: #faefc1; /* 부드러운 연노랑 */
            color: #222222;
        }

        QTreeWidget::item:hover {
            background-color: #faefc1;
        }

        /* 세련된 스크롤바 스타일 */
        QScrollBar:vertical, QScrollBar:horizontal {
            border: none;
            background: transparent;
            width: 5px;
            height: 5px;
        }

        QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
            background: #fdcb01; /* 부드러운 노랑 */
            border-radius: 5px;
            min-height: 20px;
            min-width: 20px;
        }

        QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
            background: #fea500; /* 마우스 올리면 살짝 더 진한 노랑 */
        }

        QScrollBar::handle:vertical:pressed, QScrollBar::handle:horizontal:pressed {
            background: #ff9800; /* 클릭하면 더 오렌지빛 */
        }

        QScrollBar::add-line, QScrollBar::sub-line {
            background: none;
            border: none;
        }
        """)

        self.ui.tableWidget.setStyleSheet("""
            QTableWidget {
                background-color: #FFF8DC; /* 크림색 배경 */
                border: 2px solid #fdcb01; /* 배츠마루 테마 노랑 테두리 */
                border-radius: 0px;
                
                font: 17px "Comic Sans MS"; /* 귀여운 느낌의 폰트 */
              
      
                font: 10px "Comic Sans MS";
            }
            QHeaderView::section {
                background-color: #feeca4;
                font: bold 16px "Comic Sans MS";
            }
            QTableWidget::item:selected {
                background-color: #faefc1;
                color: rgba(0, 0, 0, 0);  /* 의문의 글자 색: 투명 */
                font-weight: bold;  /* 글자를 굵게 */
            }
            QHeaderView::section {
                background-color: #feeca4; /* 연한 노랑 */
                color: #555555;
                font: bold 16px "Comic Sans MS"; /* 심플한 귀여운 폰트 */
                padding: 8px;
                border-radius: 8px;
                text-align: center;
            
            }
        """)

        self.ui.treeWidget_task.setStyleSheet("""
               /* 전체 배경 및 기본 폰트 설정 */
        QTreeWidget {
            background-color: #FFF8DC; /* 크림색 배경 */
            border: 2px solid #fdcb01; /* 배츠마루 느낌의 노랑 테두리 */
            border-radius: 0px;
            color: #555555;
            font: 14px "Comic Sans MS"; /* 귀여운 느낌의 폰트 */
        }

        /* 헤더 스타일 */
        QHeaderView::section {
            background-color: #feeca4; /* 배츠마루 테마 연한 노랑 */
            color: #222222;
            font: bold 16px "Comic Sans MS"; /* 심플한 귀여운 느낌 */
            padding: 8px;
            border-radius: 8px;
            text-align: center;
        }

        /* 트리 아이템 스타일 */
        QTreeWidget::item {
            height: 32px;
            padding: 6px;
            border-radius: 6px;
        }

        QTreeWidget::item:selected {
            background-color: #faefc1; /* 부드러운 연노랑 */
            color: #222222;
        }

        QTreeWidget::item:hover {
            background-color: #faefc1;
        }

        /* 세련된 스크롤바 스타일 */
        QScrollBar:vertical, QScrollBar:horizontal {
            border: none;
            background: transparent;
            width: 5px;
            height: 5px;
        }

        QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
            background: #fdcb01; /* 부드러운 노랑 */
            border-radius: 5px;
            min-height: 20px;
            min-width: 20px;
        }

        QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
            background: #fea500; /* 마우스 올리면 살짝 더 진한 노랑 */
        }

        QScrollBar::handle:vertical:pressed, QScrollBar::handle:horizontal:pressed {
            background: #ff9800; /* 클릭하면 더 오렌지빛 */
        }

        QScrollBar::add-line, QScrollBar::sub-line {
            background: none;
            border: none;
        }
        """)
        self.ui.comboBox_task.setStyleSheet("""
        QComboBox {
            background-color: #FFF8DC; /* 크림색 배경 */
            border: 2px solid #fdcb01; /* 노란 테두리 */
            border-radius: 5px;
            padding: 5px;
            color: #111111;
            font: 14px "Comic Sans MS";
        }
        QComboBox:hover {
            background-color: #faefc1; /* 호버 시 밝은 노랑 */
        }
        QComboBox::drop-down {
            border: none;
        }
        QComboBox QAbstractItemView {
            background-color: #feeca4; /* 드롭다운 배경 */
            selection-background-color: #faefc1; /* 선택된 항목 배경 */
            border: 1px solid #fdcb01;
        }
    """)

        self.ui.tabWidget.setStyleSheet("""
        QTabWidget::pane {
            border: 2px solid #fdcb01; /* 노란색 테두리 */
            background-color: #FFF8DC; /* 크림색 배경 */
            border-radius: 3px;
        }
        QTabBar::tab {
            background: #feeca4; /* 연한 노랑 */
            border: 1px solid #fdcb01;
            border-top-left-radius: 13px;
            border-top-right-radius: 5px;
            padding: 10px;
            color: #555555;
            font: bold 11px "Comic Sans MS";
        }
        QTabBar::tab:selected {
            background: #faefc1; /* 선택된 탭 강조 */
            color: #222222;
            font-weight: bold;
        }
        QTabBar::tab:hover {
            background: #fce6a4; /* 호버 효과 */
        }
    """)
        self.ui.listWidget_sub.setStyleSheet("""
            QListWidget {
                background-color: #FFF8DC; /* 크림색 배경 */
                border: 2px solid #fdcb01; /* 배츠마루 테마 노랑 테두리 */
                border-radius: 0px;
                color: #555555;
                font: 14px "Comic Sans MS"; /* 귀여운 느낌의 폰트 */
                gridline-color: #fdcb01; /* 테이블 그리드라인 색상 */
      
                font: 14px "Comic Sans MS";
            }
            QHeaderView::section {
                background-color: #feeca4;
                font: bold 16px "Comic Sans MS";
            }
            QTableWidget::item:selected {
                background-color: #faefc1;
                color: rgba(0, 0, 0, 0);  /* 의문의 글자 색: 투명 */
                font-weight: bold;  /* 글자를 굵게 */
            }
            QHeaderView::section {
                background-color: #feeca4; /* 연한 노랑 */
                color: #222222;
                font: bold 16px "Comic Sans MS"; /* 심플한 귀여운 폰트 */
                padding: 8px;
                border-radius: 8px;
                text-align: center;
            
            }
            /* 개별 아이템 스타일 */
            QListWidget::item {
                color: #333333; /* 기본 아이템 글자색 */
                font: 14px "Comic Sans MS";
                padding: 6px;
            }

            QListWidget::item:selected {
                background-color: #faefc1; /* 부드러운 연노랑 */
                color: #000000; /* 선택된 아이템 글자색 */
                font-weight: bold;
            }

            QListWidget::item:hover {
                background-color: #faefc1;
                color: #222222; /* 마우스 오버 시 글자색 */
            }
        """)
        self.ui.horizontalSlider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                border: 2px solid white; /* 하양 테두리 */
                background: white; /* 하양 배경 */
                height: 2px; /* 트랙 높이 조정 */
                border-radius: 1px;
                padding: 0px; /* 여백 제거 */
            }}
            QSlider::handle:horizontal {{
                background: url(/nas/Batz_Maru/pingu/imim/slider_1.png); /* 핸들 이미지 적용 */
                background-repeat: no-repeat;
                background-position: center;
                width: 30px;  /* 핸들 크기 조정 */
                height: 30px;
                margin: -14px 0; /* 트랙 중앙에 정렬 */
                border: 2px solid transparent; /* 테두리를 투명하게 설정 */
                background-color: transparent; /* 배경색 투명 */
            }}
            QSlider::handle:horizontal:hover {{
                background: url(/nas/Batz_Maru/pingu/imim/slider_1.png); /* 동일한 이미지 유지 */
                background-repeat: no-repeat;
                background-position: center;
                width: 30px;
                height: 30px;
                margin: -14px 0;
                border: 2px solid transparent;
                background-color: transparent;
            }}
            QSlider::sub-page:horizontal {{
                background: yellow; /* 진행된 부분(노랑색) */
                border-radius: 1px;
                padding: 0px; /* 진행된 부분의 여백 제거 */
            }}
        """)

if __name__=="__main__":
    app = QApplication()  
    w = MainCtrl()
    app.exec() 