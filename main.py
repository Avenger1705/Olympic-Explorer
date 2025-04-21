
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.network.urlrequest import UrlRequest
from kivy.logger import Logger
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.graphics.texture import Texture
from kivy.uix.behaviors import ButtonBehavior
import json
from kivy.uix.image import Image
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.spinner import Spinner
from kivy.uix.modalview import ModalView
import mysql.connector
from kivy.uix.relativelayout import RelativeLayout
from PIL import Image as PillImage
from PIL import ImageDraw, ImageFont
from kivy.uix.popup import Popup
import re
import os

Window.clearcolor = (1, 1, 1, 1)  


selected_image_info = ""
State = ""
chosen_sport = ""
ai_message = ""

class EcranPermission(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        image = Image(source='img/autre/Olympic_Explorer.png', size_hint=(1, 5), pos_hint={'center_x': 0.5})
        label = Label(text='Bienvenue ! Choisissez votre statut :', color=(0, 0, 0, 1))
        btn_athlete = Button(text='Athlète', background_color=(0, 0.5, 1, 1), color=(1, 1, 1, 1),size_hint=(None, None), size=(200, 50), pos_hint={'center_x': 0.5})
        btn_visitor = Button(text='Visiteur', background_color=(0, 0.5, 1, 1), color=(1, 1, 1, 1), size_hint=(None, None), size=(200, 50), pos_hint={'center_x': 0.5})

        btn_athlete.bind(on_press=self.on_choose_athlete)
        btn_visitor.bind(on_press=self.on_choose_visitor)

        layout.add_widget(label)
        layout.add_widget(image)
        layout.add_widget(btn_athlete)
        layout.add_widget(btn_visitor)
        
        self.add_widget(layout)

    def on_choose_athlete(self, instance):
        
        global State
        self.animate_button(instance)
        State = "Athlete"
        self.show_confirmation_popup()

    def on_choose_visitor(self, instance):
        global State
        self.animate_button(instance)
        State = "Visitor"
        self.show_confirmation_popup()

    def show_confirmation_popup(self):
        confirmation_popup = ConfirmationPopup(callback_yes=self.navigate_to_next_page)
        confirmation_popup.open()

    def navigate_to_next_page(self):
        
        if State == "Athlete":
            self.manager.current = 'sport_choisir'
            self.manager.get_screen('sport_choisir')
        elif State == "Visitor":
            self.manager.current = 'ecran_meteo'
            self.manager.get_screen('ecran_meteo')

    def animate_button(self, instance):
        
        self.anim = Animation(background_color=(0, 0.8, 1, 1), duration=0.5)
        self.anim += Animation(background_color=(0, 0.5, 1, 1), duration=0.5)
        self.anim.start(instance)

class SelectableImageButton(ButtonBehavior, Image):
    def __init__(self, id=None, **kwargs):
        super().__init__(**kwargs)
        self.selected = False
        self.id = id

class ConfirmationPopup(Popup):
    def __init__(self, callback_yes, **kwargs):
        super(ConfirmationPopup, self).__init__(**kwargs)
        self.callback_yes = callback_yes
        self.size_hint = (None, None) 
        self.size = (400, 300) 
        self.auto_dismiss = True 
        self.title = 'Notification' 
        self.title_size = 24  

        layout = BoxLayout(orientation='vertical', spacing=20, padding=[20, 20, 20, 20])
        label = Label(text='êtes-vous sûre?', font_size=18)
        btn_yes = Button(text='Oui', on_release=self.on_yes, font_size=16, size_hint_y=None, height=50)
        btn_no = Button(text='Non', on_release=self.dismiss, font_size=16, size_hint_y=None, height=50)

        layout.add_widget(label)
        layout.add_widget(btn_yes)
        layout.add_widget(btn_no)

        self.content = layout
    def on_yes(self, _):
        self.dismiss()
        self.callback_yes()

class EcranMeteo(Screen):
    def __init__(self, **kwargs):
        self.selected_image_ids = ""
        super(EcranMeteo, self).__init__(**kwargs)
        self.current_page = 1 
        self.default_text_filter = ""  
        self.default_sport_filter = ""  
        self.default_date_filter = ""  
        self.default_venue_filter = ""  
        self.page_size = 8  
        self.orientation = 'vertical'

        self.page_layout = BoxLayout(size_hint=(1, 0.1))
        self.add_widget(self.page_layout)

        self.prev_page_button = Button(text='Page Précédente', size_hint=(0.2, None), height=50)
        self.prev_page_button.bind(on_press=self.show_previous_page)

        self.page_label = Label(text=f'Page {self.current_page}', size_hint=(0.5, None), height=50, color=(0, 0, 0, 1))

        self.next_page_button = Button(text='Page Suivante', size_hint=(0.2, None), height=50)
        self.next_page_button.bind(on_press=self.show_next_page)

        self.db_connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="jeux_olympiques"
        )
        self.db_cursor = self.db_connection.cursor()

        self.setup_ui()
    
    def setup_ui(self):
        top_layout = BoxLayout(orientation='horizontal', size_hint=(1, None), height=50)
        self.search_bar = TextInput(hint_text='Chercher', multiline=False, size_hint=(0.8, 1))
        self.search_bar.bind(text=self.on_search_text)
        top_layout.add_widget(self.search_bar)
        self.end_image = Image(source='img/autre/check.png', size_hint=(0.05, 1))
        self.end_image.keep_ratio = True  # Garantir que l'icône garde son ratio.
        top_layout.add_widget(self.end_image)
        self.end_image.bind(on_touch_down=self.open_weather_screen)

        spinner_layout = self.setup_spinners()

        self.results_scrollview = ScrollView(size_hint=(1, 0.7), do_scroll_x=False)
        self.results_box = BoxLayout(orientation='vertical', size_hint_y=None)
        self.results_box.bind(minimum_height=self.results_box.setter('height'))
        self.results_scrollview.add_widget(self.results_box)

        main_layout = BoxLayout(orientation='vertical')
        main_layout.add_widget(top_layout)
        main_layout.add_widget(spinner_layout)
        main_layout.add_widget(self.results_scrollview)
        
        page_navigation_layout = BoxLayout(size_hint=(1, None), height=50, spacing=10)
        page_navigation_layout.add_widget(self.prev_page_button)
        self.prev_page_button.disabled = True  # Désactiver le bouton de page précédente par défaut.
        page_navigation_layout.add_widget(self.page_label)
        page_navigation_layout.add_widget(self.next_page_button)

        main_layout.add_widget(page_navigation_layout)
        
        self.add_widget(main_layout)
        
        self.load_data_from_database()
    def on_search_text(self, instance, value):
        self.load_data_from_database()
    def show_previous_page(self,_):
        if self.current_page > 1:
            self.current_page -= 1
            self.load_data_from_database()
            self.next_page_button.disabled = False
        if self.current_page == 1:
            self.prev_page_button.disabled = True

    def show_next_page(self,_):
        if len(self.results_box.children) == self.page_size:
            self.current_page += 1
            self.load_data_from_database()
            self.prev_page_button.disabled = False
        else:
            self.next_page_button.disabled = True
    def setup_spinners(self):
        spinner_layout = BoxLayout(orientation='horizontal', size_hint=(1, None), height=50)
        
        sports_list_1 = ["Sports", "Breaking", "Escalade", "skateboard", "surf", 
                        "Athlétisme", "aviron", "badminton", "basketball", 
                        "Basketball 3x3", "boxe", "Canoë course en ligne", "Canoë slalom", 
                        "cyclisme sur piste", "cyclisme sur route", "BMX freestyle", 
                        "BMX racing", "VTT", "escrime", "football", 
                        "golf", "gymnastique artistique", "gymnastique rythmique", 
                        "Gymnastique trampoline", "haltérophilie", "handball", "hockey", "judo", 
                        "lutte", "pentathlon moderne", "rugby", "natation", 
                        "natation artistique", "natation marathon", "plongeon", 
                        "Water-polo", "sports équestres", "taekwondo", "tennis", 
                        "tennis de table", "tir", "Tir à l'arc", "triathlon", "voile", 
                        "volleyball", "Beach Volleyball"]
        self.spinner_1 = Spinner(text='Sports', values=sports_list_1, size_hint=(0.3, 1))
        self.spinner_1.bind(text=self.load_data_from_database)

        sports_list_2 = ["Dates", "2024-07-24", "2024-07-25", "2024-07-26", "2024-07-27",
                        "2024-07-28", "2024-07-29", "2024-07-30", "2024-07-31",
                        "2024-08-01", "2024-08-02", "2024-08-03", "2024-08-04",
                        "2024-08-05", "2024-08-06", "2024-08-07", "2024-08-08",
                        "2024-08-09", "2024-08-10", "2024-08-11"]
        self.spinner_2 = Spinner(text='Dates', values=sports_list_2, size_hint=(0.3, 1))
        self.spinner_2.bind(text=self.load_data_from_database)

        sports_list_3 = ["Stades", "Arena Porte de La Chapelle", "Grand Palais", "Concorde", "Invalides Pont Alexandre III", "Trocadéro",
                        "Arena Champ De Mars", "Stade Tour Eiffel", "Hôtel de ville-Invalides", "Arena Bercy",
                        "Stade Roland-Garros", "Parc des Princes", "Arena Paris Sud", "Stade Yves du Manoir",
                        "Paris La Défense Arena", "Stade de France", "Centre Aquatique", "Site d'escalade",
                        "Arena Paris Nord", "Stade nautique Bassin eau calme", "Stade nautique Bassin eau vive", "Château de Versailles",
                        "Colline d'Elancourt", "Stade BMX", "Vélodrome National",
                        "Golf National", "Teahupoo", "Stade de Bordeaux", "Stade de la Beaujoire", "Stade Pierre Mauroy",
                        "Centre National de tir", "Stade de Lyon", "Stade Geoffroy Guichard", "Stade de Nice",
                        "Stade de Marseille", "Marina de Marseille"]
        self.spinner_3 = Spinner(text='Stades', values=sports_list_3, size_hint=(0.3, 1))
        self.spinner_3.bind(text=self.load_data_from_database)
        spinner_layout.add_widget(self.spinner_1)
        spinner_layout.add_widget(self.spinner_2)
        spinner_layout.add_widget(self.spinner_3)

        return spinner_layout


    
    def load_data_from_database(self, *args):
        
        if not self.db_connection.is_connected():
        
            self.db_connection.connect()
            self.db_cursor = self.db_connection.cursor()
        self.results_box.clear_widgets()
        text_filter = self.search_bar.text
        sport_filter = self.spinner_1.text if self.spinner_1.text != 'Sports' else None
        date_filter = self.spinner_2.text if self.spinner_2.text != 'Dates' else None
        venue_filter = self.spinner_3.text if self.spinner_3.text != 'Stades' else None
        if (
            text_filter != self.default_text_filter
            or sport_filter != self.default_sport_filter
            or date_filter != self.default_date_filter
            or venue_filter != self.default_venue_filter
        ):
            self.current_page = 1
        
        self.default_text_filter = text_filter
        self.default_sport_filter = sport_filter
        self.default_date_filter = date_filter
        self.default_venue_filter = venue_filter
        
        query_count = "SELECT COUNT(*) FROM evenements WHERE 1=1"
        params_count = []

        if self.default_sport_filter:

            query_count += " AND evenement = %s"
            params_count.append(self.default_sport_filter)

        if self.default_date_filter:
            query_count += " AND date = %s"
            params_count.append(self.default_date_filter)

        if self.default_venue_filter:
            query_count += " AND stades = %s"
            params_count.append(self.default_venue_filter)

        if self.default_text_filter:
            query_count += " AND (nom LIKE %s OR evenement LIKE %s OR date LIKE %s OR villes LIKE %s OR temps LIKE %s OR stades LIKE %s)"
            like_filter = f'%{self.default_text_filter}%'  
            params_count.extend([like_filter, like_filter, like_filter, like_filter, like_filter, like_filter])

        self.db_cursor.execute(query_count, params_count)
        total_events_count = self.db_cursor.fetchone()[0]

        total_pages = (total_events_count + self.page_size - 1) // self.page_size

        self.page_label.text = f'Page {self.current_page} of {total_pages}'

        query_events = "SELECT * FROM evenements WHERE 1=1"
        params_events = []

        if self.default_sport_filter:

            query_events += " AND evenement = %s"
            params_events.append(self.default_sport_filter)

        if self.default_date_filter:

            query_events += " AND date = %s"
            params_events.append(self.default_date_filter)

        if self.default_venue_filter:

            query_events += " AND stades = %s"
            params_events.append(self.default_venue_filter)

        if self.default_text_filter:
            query_events += " AND (nom LIKE %s OR evenement LIKE %s OR date LIKE %s OR villes LIKE %s OR temps LIKE %s OR stades LIKE %s)"
            like_filter = f'%{self.default_text_filter}%'
            params_events.extend([like_filter, like_filter, like_filter, like_filter, like_filter, like_filter])

        query_events += " ORDER BY date LIMIT %s OFFSET %s"
        params_events.extend([self.page_size, (self.current_page - 1) * self.page_size])

        self.db_cursor.execute(query_events, params_events)
        events = self.db_cursor.fetchall()

        self.image_event_ids = {}
        self.image_event_info = {}

        for id_event ,event , event_name, date_of_event, time_of_event, stade_of_event, ville_of_event in events:
            date_of_event_str = str(date_of_event)
            image = self.draw_text_on_image(event , event_name, date_of_event_str, time_of_event, stade_of_event, ville_of_event)
            texture = Texture.create(size=(image.width, image.height))
            texture.blit_buffer(image.tobytes(), colorfmt='rgb', bufferfmt='ubyte')

            texture.flip_vertical()

            selectable_image = SelectableImageButton(id=id_event, texture=texture, size=(image.width, image.height))
            selectable_image.bind(on_press=self.on_image_click)
            if f"|{id_event}|" in self.selected_image_ids:
                selectable_image.selected = True
                selectable_image.color = (0, 0, 1, 1)
            image_info = f"Event:{event} Event Name: {event_name} Date: {date_of_event} Time: {time_of_event} Stade: {stade_of_event} Ville: {ville_of_event}"
            
            self.image_event_info[selectable_image] = image_info

            self.results_box.add_widget(selectable_image)

            self.results_box.height = len(events) * (selectable_image.height - 38)
            
        if total_pages == 1:
            self.prev_page_button.disabled = True
            self.next_page_button.disabled = True
        elif self.current_page == 1:
            self.prev_page_button.disabled = True
            self.next_page_button.disabled = False
        elif self.current_page == total_pages:
            self.prev_page_button.disabled = False
            self.next_page_button.disabled = True
        else:
            self.prev_page_button.disabled = False
            self.next_page_button.disabled = False

    def on_image_click(self, instance):
        
        global selected_image_info
        instance.selected = not instance.selected
        if instance.selected:
            instance.color = (0, 0, 1, 1)
            self.selected_image_ids += f"|{instance.id}|"
            selected_image_info += self.image_event_info[instance] + "\n"
        else:
            instance.color = (1, 1, 1, 1)
            self.selected_image_ids = self.selected_image_ids.replace(f"|{instance.id}|", "")
            selected_image_info = selected_image_info.replace(self.image_event_info[instance] + "\n", "")

    def draw_text_on_image(self, event, event_name, date_of_event, time_of_event, stade_of_event, ville_of_event):
        background_image_path = "img/autre/evenement.png"
        background_image = PillImage.open(background_image_path)

        stade_image_extensions = [".jpg", ".jpeg",".png"]
        stade_image_extension = None
        for ext in stade_image_extensions:
            stade_image_name_with_ext = stade_of_event + ext
            stade_image_path = os.path.join("img/stades", stade_image_name_with_ext)
            if os.path.exists(stade_image_path):
                stade_image_extension = ext
                break

        if stade_image_extension is None:
            raise ValueError(f"No image found for stade '{stade_of_event}'")
        

        stade_image_path = os.path.join("img/stades", stade_of_event + stade_image_extension)
        stade_image = PillImage.open(stade_image_path)

        stade_image = stade_image.resize((350, 285))

        background_image.paste(stade_image, (0, 0))

        draw = ImageDraw.Draw(background_image)

        font_size = 16
        font = ImageFont.truetype("font.ttf", font_size)

        draw.text((510, 28), event, font=font, fill=(255, 255, 255))
        draw.text((510, 79), stade_of_event, font=font, fill=(255, 255, 255))
        draw.text((510, 120), ville_of_event, font=font, fill=(255, 255, 255))
        draw.text((510, 167), date_of_event, font=font, fill=(255, 255, 255))
        draw.text((510, 213), time_of_event, font=font, fill=(255, 255, 255))
        draw.text((510, 259), event_name, font=font, fill=(255, 255, 255))
        
        return background_image

    def on_leave(self,*args, **kwargs):

        self.db_cursor.close()
        self.db_connection.close()
        super().on_leave(*args, **kwargs)
    def show_dialog(self, message):
        modal = ModalView(size_hint=(None, None), size=(400, 200))

        content = BoxLayout(orientation='vertical')

        label = Label(text=message)

        close_button = Button(text='Close', size_hint=(None, None), size=(150, 50))
        close_button.bind(on_press=modal.dismiss)

        content.add_widget(label)
        content.add_widget(close_button)
        modal.add_widget(content)
        modal.open() 

    def open_weather_screen(self, _, touch):

        if self.end_image.collide_point(*touch.pos):

            if self.selected_image_ids == '':

                self.show_dialog("Veuillez-choisir un évenement au moin")
                return 
            
            villes = re.findall(r'Ville:\s+(\S+)', selected_image_info)
            self.city_list = list(set(villes))
            weather_screen = self.manager.get_screen('weather_screen')
            weather_screen.reset_screen()

            weather_screen.obtenir_meteo(self.city_list[0])
            weather_screen.bouton_precedent.disabled = True 
            if len(self.city_list) == 1:
                weather_screen.bouton_suivant.disabled = True
            else:
                weather_screen.bouton_suivant.disabled = False
            self.manager.current = 'weather_screen'

class EcranMeteo2(Screen):
    def __init__(self, **kwargs):
        self.selected_image_ids = ""
        super(EcranMeteo2, self).__init__(**kwargs)
        self.current_page = 1
        self.default_text_filter = ""
        self.page_size = 8
        self.orientation = 'vertical'
        self.page_layout = BoxLayout(size_hint=(1, 0.1))
        self.add_widget(self.page_layout)
        self.prev_page_button = Button(text='Page Précédente', size_hint=(0.2, None), height=50)
        self.prev_page_button.bind(on_press=self.show_previous_page)

        self.page_label = Label(text=f'Page {self.current_page}', size_hint=(0.5, None), height=50, color=(0, 0, 0, 1))

        self.next_page_button = Button(text='Page Suivante', size_hint=(0.2, None), height=50)
        self.next_page_button.bind(on_press=self.show_next_page)

        self.db_connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="jeux_olympiques"
        )
        self.db_cursor = self.db_connection.cursor()

        self.setup_ui()
    
    def setup_ui(self):
        top_layout = BoxLayout(orientation='horizontal', size_hint=(1, None), height=50)
        self.search_bar = TextInput(hint_text='Chercher', multiline=False, size_hint=(0.8, 1))
        self.search_bar.bind(text=self.on_search_text)
        top_layout.add_widget(self.search_bar)
        self.end_image = Image(source='img/autre/check.png', size_hint=(0.05, 1))
        self.end_image.keep_ratio = True
        top_layout.add_widget(self.end_image)
        self.end_image.bind(on_touch_down=self.open_weather_screen)

        self.results_scrollview = ScrollView(size_hint=(1, 0.7), do_scroll_x=False)
        self.results_box = BoxLayout(orientation='vertical', size_hint_y=None)
        self.results_box.bind(minimum_height=self.results_box.setter('height'))
        self.results_scrollview.add_widget(self.results_box)

        main_layout = BoxLayout(orientation='vertical')
        main_layout.add_widget(top_layout)
        main_layout.add_widget(self.results_scrollview)
        page_navigation_layout = BoxLayout(size_hint=(1, None), height=50, spacing=10)
        page_navigation_layout.add_widget(self.prev_page_button)
        self.prev_page_button.disabled = True
        page_navigation_layout.add_widget(self.page_label)
        page_navigation_layout.add_widget(self.next_page_button)

        main_layout.add_widget(page_navigation_layout)
        
        self.add_widget(main_layout)
        
        self.load_data_from_database()
    def show_previous_page(self, instance):
        if self.current_page > 1:
            self.current_page -= 1
            self.load_data_from_database()
            self.next_page_button.disabled = False
        if self.current_page == 1:
            self.prev_page_button.disabled = True

    def show_next_page(self, instance):
        if len(self.results_box.children) == self.page_size:
            self.current_page += 1
            self.load_data_from_database()
            self.prev_page_button.disabled = False
        else:
            self.next_page_button.disabled = True

    def on_search_text(self, instance, value):
        self.load_data_from_database()
    
    def load_data_from_database(self):
        
        if not self.db_connection.is_connected():
            self.db_connection.connect()
            self.db_cursor = self.db_connection.cursor()
        params = [self.page_size, (self.current_page - 1) * self.page_size]
        self.results_box.clear_widgets()
        text_filter = self.search_bar.text

        if (
            text_filter != self.default_text_filter
        ):
            self.current_page = 1
        
        self.default_text_filter = text_filter
        query_count = "SELECT COUNT(*) FROM evenements WHERE evenement = %s"
        params_count = [chosen_sport]

        if self.default_text_filter:
            query_count += " AND (nom LIKE %s OR evenement LIKE %s OR date LIKE %s OR villes LIKE %s OR temps LIKE %s OR stades LIKE %s)"
            like_filter = f'%{self.default_text_filter}%'
            params_count.extend([like_filter, like_filter, like_filter, like_filter, like_filter, like_filter])

        self.db_cursor.execute(query_count, params_count)
        total_events_count = self.db_cursor.fetchone()[0]

        total_pages = (total_events_count + self.page_size - 1) // self.page_size

        self.page_label.text = f'Page {self.current_page} of {total_pages}'
        query_events = "SELECT * FROM evenements WHERE evenement = %s"
        params_events = [chosen_sport]

        if self.default_text_filter:
            query_events += " AND (nom LIKE %s OR evenement LIKE %s OR date LIKE %s OR villes LIKE %s OR temps LIKE %s OR stades LIKE %s)"
            like_filter = f'%{self.default_text_filter}%'
            params_events.extend([like_filter, like_filter, like_filter, like_filter, like_filter, like_filter])
        self.db_cursor.execute(query_events, params_events)
        events = self.db_cursor.fetchall()
        for id_event ,event , event_name, date_of_event, time_of_event, stade_of_event, ville_of_event in events:
            global selected_image_info
            selected_image_info += f"Event:{event} Event Name: {event_name} Date: {date_of_event} Time: {time_of_event} Stade: {stade_of_event} Ville: {ville_of_event}\n"

        query_events = "SELECT * FROM evenements WHERE evenement = %s"
        params_events = [chosen_sport]

        if self.default_text_filter:
            query_events += " AND (nom LIKE %s OR evenement LIKE %s OR date LIKE %s OR villes LIKE %s OR temps LIKE %s OR stades LIKE %s)"
            like_filter = f'%{self.default_text_filter}%'
            params_events.extend([like_filter, like_filter, like_filter, like_filter, like_filter, like_filter])

        query_events += " ORDER BY date LIMIT %s OFFSET %s"
        params_events.extend([self.page_size, (self.current_page - 1) * self.page_size])

        self.db_cursor.execute(query_events, params_events)
        events = self.db_cursor.fetchall()
        self.image_event_ids = {}
        self.image_event_info = {}
        for id_event ,event , event_name, date_of_event, time_of_event, stade_of_event, ville_of_event in events:
            date_of_event_str = str(date_of_event)

            image = self.draw_text_on_image(event , event_name, date_of_event_str, time_of_event, stade_of_event, ville_of_event)

            texture = Texture.create(size=(image.width, image.height))
            texture.blit_buffer(image.tobytes(), colorfmt='rgb', bufferfmt='ubyte')

            texture.flip_vertical()


            kivy_image = Image(texture=texture, size=(image.width, image.height))

            self.results_box.add_widget(kivy_image)

            self.results_box.height = len(events) * (kivy_image.height - 24)

            
        if total_pages == 1:
            self.prev_page_button.disabled = True
            self.next_page_button.disabled = True
        elif self.current_page == 1:
            self.prev_page_button.disabled = True
            self.next_page_button.disabled = False
        elif self.current_page == total_pages:
            self.prev_page_button.disabled = False
            self.next_page_button.disabled = True
        else:
            self.prev_page_button.disabled = False
            self.next_page_button.disabled = False


    def draw_text_on_image(self, event, event_name, date_of_event, time_of_event, stade_of_event, ville_of_event):
        background_image_path = "img/autre/evenement.png"
        background_image = PillImage.open(background_image_path)
        
        stade_image_extensions = [".jpg", ".jpeg",".png"]
        stade_image_extension = None
        for ext in stade_image_extensions:
            stade_image_name_with_ext = stade_of_event + ext
            stade_image_path = os.path.join("img/stades", stade_image_name_with_ext)
            if os.path.exists(stade_image_path):
                stade_image_extension = ext
                break

        if stade_image_extension is None:
            raise ValueError(f"No image found for stade '{stade_of_event}'")

        stade_image_path = os.path.join("img/stades", stade_of_event + stade_image_extension)
        stade_image = PillImage.open(stade_image_path)

        stade_image = stade_image.resize((350, 285))

        background_image.paste(stade_image, (0, 0))

        draw = ImageDraw.Draw(background_image)

        font_size = 16
        font = ImageFont.truetype("font.ttf", font_size)

        draw.text((510, 28), event, font=font, fill=(255, 255, 255))
        draw.text((510, 79), stade_of_event, font=font, fill=(255, 255, 255))
        draw.text((510, 120), ville_of_event, font=font, fill=(255, 255, 255))
        draw.text((510, 167), date_of_event, font=font, fill=(255, 255, 255))
        draw.text((510, 213), time_of_event, font=font, fill=(255, 255, 255))
        draw.text((510, 259), event_name, font=font, fill=(255, 255, 255))
        
        return background_image
    def on_leave(self):
        self.db_cursor.close()
        self.db_connection.close()

    def on_leave(self):

        self.db_cursor.close()
        self.db_connection.close()
    def open_weather_screen(self, _, touch):
        
        if self.end_image.collide_point(*touch.pos):
            villes = re.findall(r'Ville:\s+(\S+)', selected_image_info)
            self.city_list = list(set(villes))
            weather_screen = self.manager.get_screen('weather_screen')
            weather_screen.reset_screen()
            weather_screen.obtenir_meteo(self.city_list[0])
            weather_screen.bouton_precedent.disabled = True
            if len(self.city_list) == 1:
                weather_screen.bouton_suivant.disabled = True
            else:
                weather_screen.bouton_suivant.disabled = False
            self.manager.current = 'weather_screen'
            


            
class Sportchoisir(Screen):
    def __init__(self, **kwargs):
        super(Sportchoisir, self).__init__(**kwargs)

        self.layout = BoxLayout(orientation='vertical', spacing=10, padding=10)

        self.image_meteo = Image(size_hint=(1, 0.5))
        sports_list = ["Breaking", "Escalade", "skateboard", "surf", 
                       "Athlétisme", "aviron", "badminton", "basketball", 
                       "Basketball 3x3", "boxe", "Canoë course en ligne", "Canoë slalom", 
                       "cyclisme sur piste", "cyclisme sur route", "BMX freestyle", 
                       "BMX racing", "VTT", "escrime", "football", 
                       "golf", "gymnastique artistique", "gymnastique rythmique", 
                       "Gymnastique trampoline", "haltérophilie", "handball", "hockey", "judo", 
                       "lutte", "pentathlon moderne", "rugby", "natation", 
                       "natation artistique", "natation marathon", "plongeon", 
                       "Water-polo", "sports équestres", "taekwondo", "tennis", 
                       "tennis de table", "tir", "Tir à l'arc", "triathlon", "voile", 
                       "volleyball", "Beach Volleyball"]
        self.sport_spinner = Spinner(text='Veuillez choisir un sport', values=sports_list, 
                                     size_hint=(1, None), height=40, pos_hint={'center_x': 0.5, 'y': 10})

        self.confirmation_button = Button(text='Confirmer', size_hint=(1, None), 
                                          height=40, 
                                          background_color=(0, 0.5, 1, 1), color=(1, 1, 1, 1),
                                          pos_hint={'center_x': 0.5, 'y': 0})
        
        self.confirmation_button.bind(on_press=self.confirm_sport_choice)

        self.layout.add_widget(self.sport_spinner)
        self.layout.add_widget(self.confirmation_button)

        self.add_widget(self.layout)

    def confirm_sport_choice(self, _):
        global chosen_sport
        chosen_sport = self.sport_spinner.text
        
        if chosen_sport == 'Veuillez choisir un sport':
            self.show_dialog("Veuillez choisir un sport.")
        else:
            ecran_meteo2 = self.manager.get_screen('ecran_meteo2')
            ecran_meteo2.load_data_from_database()
            self.manager.current = 'ecran_meteo2'
            
    def show_dialog(self, message):
        modal = ModalView(size_hint=(None, None), size=(400, 200))
        content = BoxLayout(orientation='vertical')
        label = Label(text=message)
        close_button = Button(text='Close', size_hint=(None, None), size=(150, 50))
        close_button.bind(on_press=modal.dismiss)

        content.add_widget(label)
        content.add_widget(close_button)
        modal.add_widget(content)
        modal.open()
        

class Weatherscreen(Screen):
    
    def __init__(self, **kwargs):
        
        super().__init__(**kwargs)
    def setup_ui(self):
        self.layout = BoxLayout(orientation='vertical', spacing=10, padding=10)

        self.top_bar = BoxLayout(orientation='horizontal', size_hint=(1, None), height=50)
        self.image_back = Image(source="img/autre/retour.png", size_hint=(None, 1), width=50)
        self.image_chat_ai = Image(source='img/autre/OE_AI.png', size_hint=(None, 1), width=50, on_press=self.open_chat_ai)
        self.image_chat_ai.bind(on_touch_down=self.open_chat_ai)
        self.top_bar.add_widget(self.image_back)
        self.image_back.bind(on_touch_down=self.open_selection_screen)
        for _ in range(7):
            self.top_bar.add_widget(Label())
        self.top_bar.add_widget(self.image_chat_ai)
        self.layout.add_widget(self.top_bar)

        self.label_meteo = Label(text='', size_hint=(1, 0.8), color=(0, 0, 0, 1), font_size='24sp')
        self.layout.add_widget(self.label_meteo)

        barre_navigation = BoxLayout(orientation='horizontal', size_hint=(1, 0.1))
        self.bouton_precedent = Button(text='<', size_hint=(0.1, 1), on_press=self.show_previous_city)
        self.bouton_suivant = Button(text='>', size_hint=(0.1, 1), on_press=self.show_next_city)
        barre_navigation.add_widget(self.bouton_precedent)
        barre_navigation.add_widget(self.bouton_suivant)
        self.layout.add_widget(barre_navigation)
        self.add_widget(self.layout)

        villes = re.findall(r'Ville:\s+(\S+)', selected_image_info)
        self.city_list = list(set(villes))
        self.current_city_index = 0
        self.update_weather_data()
    def reset_screen(self):
        self.setup_ui()
    def open_selection_screen(self, _, touch):
        
        if self.image_back.collide_point(*touch.pos):
            self.clear_widgets()
            if State == "Athlete":
                self.manager.current = 'ecran_meteo2'
            else:
                self.manager.current = 'ecran_meteo'

    def show_previous_city(self, _):
        
        if self.current_city_index == len(self.city_list) - 1:
            self.bouton_suivant.disabled = False
        if self.current_city_index > 0:
            self.current_city_index -= 1
            if self.current_city_index == 0:
                self.bouton_precedent.disabled = True
            self.update_weather_data()

    def show_next_city(self, _):
        
        villes = re.findall(r'Ville:\s+(\S+)', selected_image_info)
        self.city_list = list(set(villes))
        if self.current_city_index < len(self.city_list) - 1:
            self.current_city_index += 1
            self.update_weather_data()
            self.bouton_precedent.disabled = False
        if self.current_city_index == len(self.city_list) - 1:
            self.bouton_suivant.disabled = True

    def update_weather_data(self):
        
        if self.city_list:
            nom_ville = self.city_list[self.current_city_index]
            self.obtenir_meteo(nom_ville)



            
    def obtenir_meteo(self, nom_ville):

        url_api = f"http://api.openweathermap.org/data/2.5/weather?q={nom_ville}&appid=9d320a8cc7fb3d4954ae64de36ebeda8&units=metric"

        def reussite_requete(_req,result):
            Logger.info(f"Requête réussie. Résultat : {result}")
            try:
                main_data = result.get('main', {})
                ville = result.get('name','')
                temperature = main_data.get('temp', '')
                feels_like = main_data.get('feels_like', '')
                temp_min = main_data.get('temp_min', '')
                temp_max = main_data.get('temp_max', '')
                humidity = main_data.get('humidity', '')

                self.label_meteo.text = ('        Météo :\n\n'
                                         f'Ville : {ville}\n'
                                         f'Température : {temperature}°C\n'
                                         f'Ressenti : {feels_like}°C\n'
                                         f'Température Min : {temp_min}°C\n'
                                         f'Température Max : {temp_max}°C\n'
                                         f'Humidité : {humidity}%')
            except Exception as e:
                Logger.error(f"Erreur lors du traitement de la réponse : {e}")
                self.label_meteo.text = 'Erreur de traitement des données météo'

        def echec_requete(_req,result):
            Logger.error(f"Échec de la requête. Résultat : {result}")
            self.label_meteo.text = 'Erreur de requête météo'

        UrlRequest(url_api, reussite_requete, echec_requete)
    def open_chat_ai(self, _, touch):
        if self.image_chat_ai.collide_point(*touch.pos):
            ecran_Ai = self.manager.get_screen('ecran_ai')

            if not getattr(ecran_Ai, 'is_opened_before', False):
                Clock.schedule_once(ecran_Ai.send_initial_ai_message, 0.5)
                ecran_Ai.is_opened_before = True

            self.manager.current = 'ecran_ai'


class EcranAI(Screen):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = FloatLayout(size=Window.size)
        self.chat_layout = BoxLayout(orientation='vertical', spacing=10, padding=10, size_hint=(1, 0.9))
        self.chat_scroll_view = ScrollView()
        self.chat_box = BoxLayout(orientation='vertical', spacing=10, size_hint_y=None)
        self.chat_box.bind(minimum_height=self.chat_box.setter('height'))
        self.chat_scroll_view.add_widget(self.chat_box)
        self.message_input = TextInput(hint_text='Écrivez votre message ici', multiline=False,
                                       size_hint=(0.8, None), height=30, background_color=(0.9, 0.9, 0.9, 1))
        self.message_input.bind(text=self.validate_message_input)
        self.message_input.bind(on_text_validate=self.on_enter_press)
        self.send_button = Button(text='Envoyer', size_hint=(0.2, None), height=30, background_color=(0, 0.5, 1, 1), color=(1, 1, 1, 1))
        
        self.retour_button = Button(text='Retour', size_hint=(1, 0.1), background_color=(0, 0.5, 1, 1), color=(1, 1, 1, 1))
        self.chat_scroll_view.bind(scroll_y=self.check_if_at_bottom)
        self.retour_button.bind(on_press=self.animate_button)
        self.send_button.bind(on_press=self.animate_button)
        self.send_button.bind(on_release=self.on_button_release)
        
        self.floating_button = SelectableImageButton(source='img/autre/arrow.png', size_hint=(None, None), size=(50, 50), pos_hint={'center_x': 0.5, 'top': 0.3})
        self.floating_button.bind(on_press=self.scroll_to_bottom)

        self.layout.add_widget(self.chat_layout)
        if self.chat_layout.parent:
            self.chat_layout.parent.remove_widget(self.chat_layout)
        
        self.chat_layout.add_widget(self.chat_scroll_view)
        self.chat_layout.add_widget(self.message_input)
        self.chat_layout.add_widget(self.send_button)
        self.chat_layout.add_widget(self.retour_button)

        self.layout.add_widget(self.floating_button)
        self.add_widget(self.layout)

        self.add_widget(self.chat_layout)
        if self.floating_button.parent:
            self.floating_button.parent.remove_widget(self.floating_button)
        self.add_widget(self.floating_button)

        
    def check_if_at_bottom(self, _, value):
        if value > 0.3:
            anim_show = Animation(pos_hint={'top': 0.3, 'center_x': 0.5}, opacity=1, duration=0.5)
            anim_show.start(self.floating_button)
        else:
            anim_hide = Animation(pos_hint={'top': 0.1, 'center_x': 0.5}, opacity=0, duration=0.5)
            anim_hide.start(self.floating_button)

    def animate_button(self, instance):
        if instance.text == 'Envoyer':
            self.send_message(instance)
        elif instance.text == 'Retour':
            self.on_retour(instance)
    def on_button_release(self, instance):
        if instance.text == 'Envoyer':
            self.send_message(instance)

    def on_enter_press(self, _):
        if not self.send_button.disabled:
            self.animate_button(self.send_button)
            

    def on_retour(self, _):
        self.manager.current = 'weather_screen'

    def send_message(self, _):
        trimmed_value = self.message_input.text
        if not bool(trimmed_value):
            self.message_input.focus = True
        else:
            user_message = self.message_input.text
            self.display_user_message(user_message)
            Clock.schedule_once(lambda dt: self.get_ai_response(user_message), 10)
            self.message_input.text = ""

    def send_initial_ai_message(self,_):
    
        villes = re.findall(r'Ville:\s+([\w-]+)', selected_image_info)
        unique_villes = list(set(villes))
        visiting_cities = ", ".join([ville.replace('-', ' ') for ville in unique_villes])
        if State == "Athlete":
            message = f"En tant qu'assistant pour l'application des Jeux Olympiques Paris 2024 qui s'appelle Olympic Explorer, tu es maintenant en mode assistant pour athlètes. L'utilisateur est un(e) athlète pratiquant {chosen_sport}. Il/elle souhaite également explorer {visiting_cities} pendant son temps libre. Offre des conseils de préparation et motivation pour les événements, ainsi que des recommandations pour des lieux à visiter et des bons plans dans les environs de {visiting_cities}. Comment puis-je aider davantage ?"
        else:
            message = f"En tant qu'assistant pour l'application des Jeux Olympiques Paris 2024 qui s'appelle Olympic Explorer, tu es maintenant en mode assistant touristique. Le visiteur va à {visiting_cities} pour voir {selected_image_info}. Propose des recommandations personnalisées basées sur ces informations, incluant des hébergements, des restaurants, des sites touristiques à ne pas manquer, et des conseils vestimentaires basés sur les prévisions météorologiques pour le jour de leur visite. Comment puis-je aider davantage ?"
        self.get_ai_response(message)

    
    def scroll_to_bottom(self, *args):
        if self.chat_scroll_view.scroll_y > 0.99:
            self.chat_scroll_view.scroll_y = 0
        else:
            Clock.schedule_once(lambda dt: setattr(self.chat_scroll_view, 'scroll_y', 0), 0.1)
        Clock.schedule_once(lambda dt: setattr(self.chat_scroll_view, 'scroll_y', 0), 0.1)

    def _trigger_scroll_to_bottom(self, _dt):
        print(f"Hauteur du contenu : {self.chat_box.height}, Position de défilement : {self.chat_scroll_view.scroll_y}")
        if self.chat_box.height > self.chat_scroll_view.height:
            anim = Animation(scroll_y=0, d=0.5, t='out_cubic')
            anim.start(self.chat_scroll_view)
        else:
            print("Le contenu n'est pas plus haut que la hauteur de la vue défilable.")

    def validate_message_input(self, instance, value):
        trimmed_value = value.lstrip()
        if len(trimmed_value) < len(value):
            instance.text = trimmed_value
            instance.cursor = (len(trimmed_value), 0)
        self.send_button.disabled = not bool(trimmed_value)

    def get_ai_response(self, user_message):
        global ai_message
        print(user_message)
        ai_message = "Réponse en cours"
        self.display_ai_message(ai_message)
        url_api = 'https://api.openai.com/v1/chat/completions'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'chat api',
        }
        data = {
            'model': 'gpt-3.5-turbo-0125',
            'messages': [{'role': 'user', 'content': user_message}],
            'temperature': 0.7
        }


        def success(_req, result):
            global ai_message
            Logger.info(f"Requête OpenAI réussie. Résultat : {result}")
            ai_message = result.get('choices', [{}])[0].get('message', {}).get('content', '')

        def failure(_req, result):
            global ai_message
            ai_message = "La connexion à l'assistant IA a échoué. Veuillez vérifier votre connexion API."
            Logger.error(f"Requête OpenAI échouée. Résultat : {result}")
            self.message_input.text = ""
            self.message_input.hint_text = "La connexion à l'assistant IA a échoué. Veuillez vérifier votre connexion API."
            self.message_input.disabled = True
            self.send_button.disabled = True

        UrlRequest(url_api, req_headers=headers, req_body=json.dumps(data), on_success=success, on_failure=failure)

    def display_user_message(self, message):
        processed_text, block_height = process_text_with_line_breaks(message)
        user_box = RelativeLayout(size_hint_y=None, height=block_height, size_hint_x=None, width=self.width * 0.8, pos_hint={'right': 1.2})

        user_label = Label(text=processed_text, color=(0, 0, 0, 1), size_hint=(None, None), halign='left', valign='top')
        user_label.text_size = (self.width * 0.8, None)
        user_label.bind(texture_size=user_label.setter('size'))
        self.scroll_to_bottom()

        def on_next_frame(_args):
            with user_box.canvas.before:
                Color(0.8, 0.8, 1, 1) 
                RoundedRectangle(pos=(user_label.x, user_label.y), size=user_label.size) 

        Clock.schedule_once(on_next_frame)

        user_box.add_widget(user_label)
        self.chat_box.add_widget(user_box)
    def display_ai_message(self, _message):
        initial_height = 18
        box_width_fraction = 0.65
        box_width = self.chat_box.width * box_width_fraction 

        ai_box = RelativeLayout(size_hint_y=None, height=initial_height, width=box_width, size_hint_x=None)

        with ai_box.canvas.before:
            Color(0.8, 1, 0.8, 1)
            rect = RoundedRectangle(pos=ai_box.pos, size=ai_box.size)
        def update_rect_size(instance, _value):
            rect.pos = instance.pos
            rect.size = instance.size
        ai_box.bind(pos=update_rect_size, size=update_rect_size)
        ai_label = Label(text='', color=(0, 0, 0, 1), halign='left', valign='top')
        ai_label.bind(size=ai_label.setter('text_size'))
        ai_label.text_size = (ai_box.width, None)
        ai_box.add_widget(ai_label)
        self.chat_box.add_widget(ai_box)
        self.send_button.disabled = True
        placeholder_text = "Réponse en cours"
        animation_steps = ['', '.', '..', '...']
        step_index = [0] 
        def animate_placeholder(_dt):
            if step_index[0] < len(animation_steps):
                ai_label.text = placeholder_text + animation_steps[step_index[0]]
                step_index[0] = (step_index[0] + 1) % len(animation_steps)
            else:
                step_index[0] = 0

        placeholder_event = Clock.schedule_interval(animate_placeholder, 0.5)

        def start_typing_message():
            Clock.unschedule(placeholder_event) 
            clear_placeholder_then_type_message() 
        def check_ai_answer(_dt):
            if ai_message != "Réponse en cours":         
                start_typing_message()
                Clock.unschedule(check_ai_answer)
            else:
                Clock.schedule_once(check_ai_answer, 0.1)
        Clock.schedule_once(check_ai_answer, 3)

        def clear_placeholder_then_type_message(index=[19], line_count=[1]):
            processed_text, _block_height = process_text_with_line_breaks(ai_message)
            if processed_text == "Réponse en cours":
                Clock.schedule_interval(animate_placeholder, 0.5)
            else:
                if index[0] > 0:
                    ai_label.text = ai_label.text[:-1]
                    index[0] -= 1
                    Clock.schedule_once(lambda dt: clear_placeholder_then_type_message(index, line_count), 0.05)
                else:
                    def update_text(_dt, text_index=[0]):
                        if text_index[0] < len(processed_text):
                            ai_label.text += processed_text[text_index[0]]
                            text_index[0] += 1
                            if processed_text[text_index[0] - 1] == '\n' or text_index[0] == 1:
                                line_count[0] += 1
                                ai_box.height = initial_height * line_count[0]
                        else:
                            Clock.unschedule(event)
                            finalize_message_display()
                            if ai_message != "La connexion à l'assistant IA a échoué. Veuillez vérifier votre connexion API.":
                                self.send_button.disabled = False

                    event = Clock.schedule_interval(update_text, 0.05)

        def finalize_message_display():
            fixed_ai_box = RelativeLayout(size_hint_y=None, size=ai_box.size, pos=ai_box.pos, width=box_width, size_hint_x=None)
            with fixed_ai_box.canvas.before:
                Color(0.8, 1, 0.8, 1)
                RoundedRectangle(pos=fixed_ai_box.pos, size=fixed_ai_box.size)
            if ai_label.parent:
                ai_label.parent.remove_widget(ai_label)

            fixed_ai_box.add_widget(ai_label)
            
            self.chat_box.remove_widget(ai_box)
            self.chat_box.add_widget(fixed_ai_box)




def process_text_with_line_breaks(text, maxlen=70):
    words = text.split()
    lines = [] 
    current_line = ""

    for word in words:
        if len(word) > maxlen:
            if current_line:
                lines.append(current_line)
                current_line = ""
            while len(word) > maxlen:
                lines.append(word[:maxlen])
                word = word[maxlen:]
            current_line = word
        else:
            if len(current_line) + len(word) + 1 > maxlen:
                lines.append(current_line)
                current_line = word
            else:
                current_line += " " + word if current_line else word

    if current_line:
        lines.append(current_line)

    line_height = 18
    block_height = len(lines) * line_height

    return "\n".join(lines), block_height




class OlympicExplorer(App):

    def build(self):
        Window.set_icon('img/autre/Olympic_Explorer.png')
        self.gestionnaire_ecrans = ScreenManager()
        self.ecran_permission = EcranPermission(name='ecran_permission')
        self.ecran_meteo = EcranMeteo(name='ecran_meteo')
        self.ecran_meteo2 = EcranMeteo2(name='ecran_meteo2')
        self.sport_choisir = Sportchoisir(name='sport_choisir')
        self.ecran_ai = EcranAI(name='ecran_ai')
        self.weather_screen = Weatherscreen(name='weather_screen')
        self.gestionnaire_ecrans.add_widget(self.ecran_permission)
        self.gestionnaire_ecrans.add_widget(self.ecran_meteo)
        self.gestionnaire_ecrans.add_widget(self.ecran_meteo2)
        self.gestionnaire_ecrans.add_widget(self.ecran_ai)
        self.gestionnaire_ecrans.add_widget(self.weather_screen)
        self.gestionnaire_ecrans.add_widget(self.sport_choisir)
        
        return self.gestionnaire_ecrans



if __name__ == '__main__':
    OlympicExplorer().run()






