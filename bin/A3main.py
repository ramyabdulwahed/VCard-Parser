#!/usr/bin/env python3

from asciimatics.widgets import Frame, ListBox, Layout, Divider, Text, \
    Button, TextBox, Widget
from asciimatics.scene import Scene
from asciimatics.screen import Screen
from asciimatics.exceptions import ResizeScreenError, NextScene, StopApplication
import sys
import sqlite3
from asciimatics.widgets import PopUpDialog


from ctypes import *
import os
from classes import *
import mysql.connector
from mysql.connector import Error
import datetime
from datetime import timedelta


vcparser = CDLL('./libvcparser.so')
#argument types for creatCard it takes a string and double pointer to a card
vcparser.createCard.argtypes = [c_char_p, POINTER(POINTER(Card))]
vcparser.createCard.restype = c_int

#argument types for validateCard it takes a pointer to a card
vcparser.validateCard.argtypes = [POINTER(Card)]
vcparser.validateCard.restype = c_int

#argument types for writeCard it takes a string and a pointer to a card
vcparser.writeCard.argtypes = [c_char_p, POINTER(Card)]
vcparser.writeCard.restype = c_int

#argument types for getFNProperty it takes a pointer to a card
vcparser.getFNProperty.argtypes = [POINTER(Card)]
vcparser.getFNProperty.restype = c_char_p

#argument types for getBirthdayProperty it takes a pointer to a card
vcparser.getBirthdayProperty.argtypes = [POINTER(Card)]
vcparser.getBirthdayProperty.restype = c_char_p

#argument types for getAnniversaryProperty it takes a pointer to a card
vcparser.getAnniversaryProperty.argtypes = [POINTER(Card)]
vcparser.getAnniversaryProperty.restype = c_char_p

#argument types for getOptionalProperties it takes a pointer to a card
vcparser.getLengthOptionalProperties.argtypes = [POINTER(Card)]
vcparser.getLengthOptionalProperties.restype = c_int

#argument types forchangeFNPropertyValue it takes a pointer to a card and a string
vcparser.changeFNPropertyValue.argtypes = [POINTER(Card), c_char_p]
vcparser.changeFNPropertyValue.restype = c_char_p

#argument types for getAnniversaryPropForSQL it takes a pointer to a card
vcparser.getAnniversaryPropForSQL.argtypes = [POINTER(Card)]
vcparser.getAnniversaryPropForSQL.restype = c_char_p
#argument types for getBirthdayPropForSQL it takes a pointer to a card
vcparser.getBirthdayPropForSQL.argtypes = [POINTER(Card)]
vcparser.getBirthdayPropForSQL.restype = c_char_p

#function to convert a python string to a c string
def makeCString(string: str):
    cstring = c_char_p (string.encode('utf-8'))
    return cstring
#function to convert a c string to a python string
def makePyString(cstring: c_char_p):
    if cstring is None:
        return ""
    string = cstring.decode('utf-8')
    return string

'''
Table FILE 
1. file_id: INT, AUTO_INCREMENT, PRIMARY KEY.
 2. file_name: VARCHAR(60), NOT NULL.  The name of the vCard file.  
3. last_modified: DATETIME. The time the file was last modified on the disk. You can get this time using 
Python's os.path.getmtime() function.
 4. creation_time: DATETIME, NOT NULL. The time/date when the file was created in the database.  We count the 
time/date when the file was added to the database as creation time.
 1
Table CONTACT 
1. contact_id: INT, AUTO_INCREMENT, PRIMARY KEY.
 2. name: VARCHAR(256), NOT NULL.  Individuals name - value of the FN property.
 3. birthday: DATETIME. The value from the BDAY property, converted into MySQL's datetime format.  We will 
assume that the birthday is a proper date-time - is has no missing values, and is not text.  It may be NULL if it is 
not specified in the original file, or if it a text date-time.
 4. anniversary: DATETIME. The value from the anniversary property, converted into MySQL's datetime format.  
We will assume that the anniversary is a proper date-time - is has no missing values, and is not text.  It may be 
NULL if it is not specified in the original file, or if it a text date-time.
 5. file_id: INT, NOT NULL. The file that was downloaded.  FOREIGN KEY REFERENCES establishes a foreign 
key to the file_id column in the FILE table.  Deleting the latter's row will automatically cascade to delete all its 
referencing contacts. 
6. Additional constraint: FOREIGN KEY (file_id) REFERENCES FILE(file_id) ON DELETE CASCADE 

'''


class ContactModel():
    def __init__(self, conn=None):
        self.conn = conn
        self.vCardFiles = []
        # Create a database in RAM.
        if self.conn:
            cursor = self.conn.cursor()
            self.conn.autocommit = True
            cursor.execute("CREATE TABLE IF NOT EXISTS FILE (file_id INT AUTO_INCREMENT PRIMARY KEY, file_name VARCHAR(60) NOT NULL, last_modified DATETIME, creation_time DATETIME NOT NULL)")
            cursor.execute("CREATE TABLE IF NOT EXISTS CONTACT (contact_id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(256) NOT NULL, birthday DATETIME, anniversary DATETIME, file_id INT NOT NULL, FOREIGN KEY (file_id) REFERENCES FILE(file_id) ON DELETE CASCADE)")

        self.loadvCards()
    def loadvCards(self):
       # self.vCardFiles =  [] #instance variable to store the valid vCard files and we can access from other methods
        vCardFiles = os.listdir("cards/" )
        for vCardFile in vCardFiles:
            if vCardFile.endswith(".vcf"):
                #card_ptr = POINTER(Card)() #tell python that card_ptr is a pointer to a card
                card_ptr = POINTER(Card)()  # This is a single pointer (Card*)
                card_ptr_ptr = pointer(card_ptr)  # This makes it a double pointer (Card**)
                vcparser.createCard(makeCString("cards/" + vCardFile), byref(card_ptr))
                errorCode = vcparser.validateCard(card_ptr)
                if errorCode == 0:
                    #print("Card is valid")
                    if vCardFile not in self.vCardFiles:  # Prevent duplicates
                        self.vCardFiles.append(vCardFile)
                        #lets insert the file into the database after extracting the needed information for both tables
                        infoForFileTable = {
                            "filename": vCardFile,
                            "last_modified": os.path.getmtime("cards/" + vCardFile),
                            #"creation_time": datetime.datetime.now()
                        }
                        birthday = makePyString(vcparser.getBirthdayPropForSQL(card_ptr))
                        anniversary = makePyString(vcparser.getAnniversaryPropForSQL(card_ptr))

                        if birthday:
                            birthday = f"{birthday[0:4]}-{birthday[4:6]}-{birthday[6:8]} {birthday[9:11]}:{birthday[11:13]}:{birthday[13:15]}"
                        else:
                            birthday = None
                        if anniversary:
                            anniversary = f"{anniversary[0:4]}-{anniversary[4:6]}-{anniversary[6:8]} {anniversary[9:11]}:{anniversary[11:13]}:{anniversary[13:15]}"
                            #print(anniversary)
                        else:
                            anniversary = None
                        infoForContactTable = {
                            "name": makePyString(vcparser.getFNProperty(card_ptr)),
                            "birthday": birthday,
                            "anniversary": anniversary,
                        }
                        self.add(infoForFileTable, infoForContactTable)
            

                    #now lets display the filename in the view



        # Current contact when editing.
        self.current_id = None

    def add(self, file,contact):
        if self.conn is None:
            return
        cursor = self.conn.cursor()
        self.conn.autocommit = True

        cursor.execute("SELECT file_name from FILE where file_name = %s", (file["filename"],))
        result = cursor.fetchone()

        if result is None:
            last_modified = os.path.getmtime("cards/" + file["filename"])
            #convert the last modified time to a string so sql intrepts it
            last_modified = datetime.datetime.fromtimestamp(last_modified)
            convert_time = last_modified - timedelta(hours=4)
            last_modified = convert_time.strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("INSERT INTO FILE (file_name, last_modified, creation_time) VALUES (%s, %s, NOW())", (file["filename"], last_modified))

            cursor.execute("SELECT file_id FROM FILE WHERE file_name = %s", (file["filename"],))
            file_id_result = cursor.fetchone()

            if file_id_result is None:
                #print("File ID not found for this vCard.")
                return  # Exit function if file doesn't exist in FILE table

            file_id = file_id_result[0]  # Extract the integer ID

            cursor.execute("INSERT INTO CONTACT (name, birthday, anniversary, file_id) VALUES (%s, %s, %s, %s)", (contact["name"], contact["birthday"], contact["anniversary"], file_id))
            #self.show_message("File added to database")
        else:
            #self.show_message("File already exists")
            return
        # self._db.cursor().execute('''
        #     INSERT INTO contacts(name, phone, address, email, notes)
        #     VALUES(:name, :phone, :address, :email, :notes)''',
        #                           contact)
        # self._db.commit()

    #for creating new vCard
    def createNew(self, file,contact):
        if self.conn is None:
            return
        cursor = self.conn.cursor()
        self.conn.autocommit = True

        cursor.execute("SELECT file_name from FILE where file_name = %s", (file["filename"],))
        result = cursor.fetchone()

        if result is None:
            cursor.execute("INSERT INTO FILE (file_name, last_modified, creation_time) VALUES (%s, NOW(), NOW())", (file["filename"],))

            cursor.execute("SELECT file_id FROM FILE WHERE file_name = %s", (file["filename"],))
            file_id_result = cursor.fetchone()

            if file_id_result is None:
                return  # Exit function if file doesn't exist in FILE table

            file_id = file_id_result[0]  # Extract the integer ID

            cursor.execute("INSERT INTO CONTACT (name, birthday, anniversary, file_id) VALUES (%s, %s, %s, %s)", (contact["name"], contact["birthday"], contact["anniversary"], file_id))
            #self.show_message("File added to database")
            self.loadvCards() 
        else:
            #self.show_message("File already exists")
            return
        # self._db.cursor().execute('''
        #     INSERT INTO contacts(name, phone, address, email, notes)
        #     VALUES(:name, :phone, :address, :email, :notes)''',
        #                           contact)
        # self._db.commit()

    def get_summary(self):
        # return self._db.cursor().execute(
        #     "SELECT name, id from contacts").fetchall()
        if self.conn is None:
            return []
       # print ("hello")

    def get_contact(self, contact_id):
        if self.conn is None:
            return 
        cursor = self.conn.cursor()
        self.conn.autocommit = True
        cursor.execute("SELECT file_id from FILE where file_name = %s", (contact["filename"],))
        file_id = cursor.fetchone()
        return file_id
    #def get_current_contact(self):
        # if self.current_id is None:
        #     return {"name": "", "address": "", "phone": "", "email": "", "notes": ""}
        # else:
        #     return self.get_contact(self.current_id)

    def update_current_contact(self, details):
        
        if self.conn is None:
            return
        cursor = self.conn.cursor()
        self.conn.autocommit = True
        last_modified = os.path.getmtime("cards/" + details["filename"])
        #convert the last modified time to a string so sql intrepts it
        #last_modified = datetime.datetime.fromtimestamp(last_modified).strftime("%Y-%m-%d %H:%M:%S")
        last_modified = datetime.datetime.fromtimestamp(last_modified)
        convert_time = last_modified - timedelta(hours=4)
        last_modified = convert_time.strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            UPDATE CONTACT 
            SET name = %s 
            WHERE file_id = (SELECT file_id FROM FILE WHERE file_name = %s)
        """, (details["newfn"],details["filename"]))
        #lets update the last modified time in the FILE table
        cursor.execute("UPDATE FILE SET last_modified = %s WHERE file_name = %s", (last_modified, details["filename"]))
    #def delete_contact(self, contact_id):
        # self._db.cursor().execute('''
        #     DELETE FROM contacts WHERE id=:id''', {"id": contact_id})
        # self._db.commit()

    def show_message(self, message):
       self.scene.add_effect(PopUpDialog(self.screen, message, ["OK"]))
class ListView(Frame):
    def __init__(self, screen, model):
        super(ListView, self).__init__(screen,
                                       screen.height * 2 // 3,
                                       screen.width * 2 // 3,
                                       on_load=self._reload_list,
                                       hover_focus=True,
                                       can_scroll=False,
                                       title="vCard List")
        # Save off the model that accesses the contacts database.
        self._model = model

        # Create the form for displaying the list of contacts.
        self._list_view = ListBox(
            Widget.FILL_FRAME,
            model.get_summary() or [],
            name="filename",
            add_scroll_bar=True,
            on_change=self._on_pick,
            on_select=self._edit)
        self._edit_button = Button("Edit", self._edit)
        self._delete_button = Button("DB queries", self._delete)
        layout = Layout([100], fill_frame=True)
        self.add_layout(layout)
        layout.add_widget(self._list_view)
        layout.add_widget(Divider())
        layout2 = Layout([1, 1, 1, 1])
        self.add_layout(layout2)
        layout2.add_widget(Button("Create", self._add), 0)
        layout2.add_widget(self._edit_button, 1)
        layout2.add_widget(self._delete_button, 2)
        layout2.add_widget(Button("Exit", self._quit), 3)
        self.fix()
        #self._on_pick()

    def process_event(self, event):
        if hasattr(event, "key_code") and event.key_code == Screen.KEY_ESCAPE:
            raise NextScene("Main")
        return super().process_event(event)

    def show_message(self, message):
        self.scene.add_effect(PopUpDialog(self.screen, message, ["OK"]))
    def _on_pick(self):
        if self._model.conn is None:
            self._delete_button.disabled = True
        if not self._model.vCardFiles:
            self._edit_button.disabled = True

        if self._model.conn is None and not self._model.vCardFiles:
            self._delete_button.disabled = True
            self._edit_button.disabled = True
    def _reload_list(self, new_value=None):
        #self._list_view.options = self._model.get_summary()
        self._list_view.options = [(file, file) for file in self._model.vCardFiles]
        self._list_view.value = new_value
        self._on_pick()

    def _add(self):
        self._model.current_id = None
        raise NextScene("create card")

    def _edit(self):
        self.save()
        self._model.current_id = self.data["filename"]
        #self.show_message(f"Editing vCard: {self._model.current_id}")
        sys.__stdout__.flush()  # Ensure it prints immediately


        raise NextScene("Edit Contact")

    def _delete(self):
        # self.save()
        # self._model.delete_contact(self.data["filename"])
        # self._reload_list()

        raise NextScene("DB queries")
    @staticmethod
    def _quit():
        raise StopApplication("User pressed quit")


class ContactView(Frame):
    def __init__(self, screen, model):
        super(ContactView, self).__init__(screen,
                                          screen.height * 2 // 3,
                                          screen.width * 2 // 3,
                                          hover_focus=True,
                                          can_scroll=False,
                                          title=" vCard details",
                                          reduce_cpu=True)

        # Save off the model that accesses the contacts database.
        
        self._model = model
        self.card_ptr = None
        file_name = self._model.current_id
        # Create the form for displaying the list of contacts.
        layout = Layout([100], fill_frame=True)
        self.add_layout(layout)
        layout.add_widget(Text("File name:", "filename", readonly=True))
        layout.add_widget(Text("Contact:", "contact"))
        layout.add_widget(Text("Birthday:", "birthday",readonly=True))
        layout.add_widget(Text("Anniversary:", "Anniversary", readonly=True))
        layout.add_widget(Text("Optional Properties:", "Optional Properties", readonly=True))
        #layout.add_widget(TextBox(
        #    Widget.FILL_FRAME, "Notes:", "notes", as_string=True, line_wrap=True))
        layout2 = Layout([1, 1, 1, 1])
        self.add_layout(layout2)
        layout2.add_widget(Button("OK", self._ok), 0)
        layout2.add_widget(Button("Cancel", self._cancel), 3)
        self.fix()
        #self.reset()

    def process_event(self, event):
        if hasattr(event, "key_code") and event.key_code == Screen.KEY_ESCAPE:
            raise NextScene("Main")
        return super().process_event(event)

    def show_message(self, message):
        self.scene.add_effect(PopUpDialog(self.screen, message, ["OK"]))
    def reset(self):
        # Do standard reset to clear out form, then populate with new data.
        #print("reset")
        super(ContactView, self).reset()
        #self.data = self._model.get_current_contact()

        filename = self._model.current_id
        if filename is None:
            return
        #print(filename)

        self.card_ptr = POINTER(Card)()  # This is a single pointer (Card*)
        file = "cards/" + filename
        vcparser.createCard(makeCString(file), byref(self.card_ptr))


        # self.data["filename"] = filename
        # FN = makePyString(vcparser.getFNProperty(card_ptr))
        # if FN is not None:
        #     self.data["contact"] = FN
        # Birthday = makePyString(vcparser.getBirthdayProperty(card_ptr))
        # if Birthday is not None:
        #     self.data["birthday"] = Birthday
        # Anniversary = makePyString(vcparser.getAnniversaryProperty(card_ptr))
        # if Anniversary is not None:
        #     self.data["Anniversary"] = Anniversary
        # optionalProperties = vcparser.getLengthOptionalProperties(card_ptr)
        # if optionalProperties is not None:

        #     self.data["Optional Properties"] = vcparser.getLengthOptionalProperties(card_ptr)

        self.data = {
        "filename": filename,
        "contact": makePyString(vcparser.getFNProperty(self.card_ptr)),
        "birthday": makePyString(vcparser.getBirthdayProperty(self.card_ptr)),
        "Anniversary": makePyString(vcparser.getAnniversaryProperty(self.card_ptr)),
        "Optional Properties": str(vcparser.getLengthOptionalProperties(self.card_ptr))  # Ensure string format
        }
    


        #self.show_message(f"Editing vCardddddd: {self._model.current_id}")




    def _ok(self):
        
        self.save()
        newFn = self.data["contact"]
        #self.show_message(f"Editing vCard: {newFn}")
        oldfn = vcparser.changeFNPropertyValue(self.card_ptr, makeCString(newFn))
        errorCode = vcparser.validateCard(self.card_ptr)
        #self.show_message(f"Editing vCard: {errorCode}")
        if errorCode == 0:
            cardInfo ={
                "filename": self.data["filename"],
                "newfn": newFn,
            }
            self.show_message(f"Card is valid")
            thefilename =  "cards/" + self.data["filename"]
            vcparser.writeCard(makeCString(thefilename), self.card_ptr)
            #update the database
            if self._model.conn is None:
                return
            cursor = self._model.conn.cursor()
            cursor.autocommit = True
            self._model.update_current_contact(cardInfo)


        else:
            self.show_message(f"Card is not valid")
            vcparser.changeFNPropertyValue(self.card_ptr,(oldfn))
        #self._model.update_current_contact(self.data)
        #raise NextScene("Main")

    @staticmethod
    def _cancel():
        raise NextScene("Main")
#createView
class CreateView(Frame):
    def __init__(self, screen, model):
        super(CreateView, self).__init__(screen,
                                          screen.height * 2 // 3,
                                          screen.width * 2 // 3,
                                          hover_focus=True,
                                          can_scroll=False,
                                          title="create vCard",
                                          reduce_cpu=True)

        # Save off the model that accesses the contacts database.
        
        self._model = model
        self.card_ptr = None
        #create a minimal vCard 
       
        file_name = self._model.current_id
        # Create the form for displaying the list of contacts.
        layout = Layout([100], fill_frame=True)
        self.add_layout(layout)
        layout.add_widget(Text("File name:", "filename"))
        layout.add_widget(Text("Contact:", "contact"))
        #layout.add_widget(TextBox(
        #    Widget.FILL_FRAME, "Notes:", "notes", as_string=True, line_wrap=True))
        layout2 = Layout([1, 1, 1, 1])
        self.add_layout(layout2)
        layout2.add_widget(Button("OK", self._ok), 0)
        layout2.add_widget(Button("Cancel", self._cancel), 3)
        self.fix()
        #self.reset()

    def process_event(self, event):
        if hasattr(event, "key_code") and event.key_code == Screen.KEY_ESCAPE:
            raise NextScene("Main")
        return super().process_event(event)

    def show_message(self, message):
        self.scene.add_effect(PopUpDialog(self.screen, message, ["OK"]))
    def reset(self):
        # Do standard reset to clear out form, then populate with new data.
        
        super(CreateView, self).reset()
        #self.show_message ("reset")

        self.card_ptr = POINTER(Card)()  # This is a single pointer (Card*)
        fileN = "cards/" + "forCreateCard.vcf"
        vcparser.createCard(makeCString(fileN), byref(self.card_ptr))

        #self.data = self._model.get_current_contact()

        self.data = {
        "filename": "",
        "contact": ""
        }


    def _ok(self):
        self.save()
        #validate the required fileds 
        #self.show_message(f"Editing vCard: {self.data['filename']} {self.data['contact']}")
        if self.data["filename"] is None:
            self.show_message(f"Please enter a filename")
            return
        if self.data["contact"] is None:
            self.show_message(f"Please enter a contact")
            return
        if not self.data["filename"].endswith(".vcf"):
            self.show_message(f"Please enter a filename with .vcf extension")
            return
        #self.show_message(f"f{self.data['filename']} {self.data['contact']}")
        path = os.path.join("cards", self.data["filename"])
        if os.path.exists(path):
            self.show_message(f"File already exists")
            return
        else:
            
            newFN = self.data["contact"]
            newFileN = self.data["filename"]
         #   self.show_message(f"got input")
            path = os.path.join("cards", newFileN)
          #  self.show_message(f"got path")
            vcparser.changeFNPropertyValue(self.card_ptr, makeCString(newFN))
            errorCode = vcparser.validateCard(self.card_ptr)
          #  self.show_message(f"Editing vCard: {errorCode}")
            if errorCode == 0:
                self.show_message(f"Card is valid")
                vcparser.writeCard(makeCString(path), self.card_ptr)
                #update the database
                if self._model.conn is None:
                    return
                cursor = self._model.conn.cursor()
                cursor.autocommit = True
                self._model.createNew({"filename": newFileN, "last_modified": os.path.getmtime(path)}, {"name": newFN, "birthday": None, "anniversary": None})

            else:
                self.show_message(f"Card is not valid")
                return



    @staticmethod
    def _cancel():
        raise NextScene("Main")






#DB QUERY

class DataBaseView(Frame):
    def __init__(self, screen, model):
        super(DataBaseView, self).__init__(screen,
                                          screen.height * 2 // 3,
                                          screen.width * 2 // 3,
                                          hover_focus=True,
                                          can_scroll=False,
                                          title="",
                                          reduce_cpu=True)

        # Save off the model that accesses the contacts database.
        
        self._model = model
        self.card_ptr = None
        #create a minimal vCard 
       
        file_name = self._model.current_id
        # Create the form for displaying the list of contacts.
        layout = Layout([100], fill_frame=True)
        self.add_layout(layout)

        self._results_box = ListBox(
            Widget.FILL_FRAME,
            [],
            name="results",
            add_scroll_bar=True
        )
        layout.add_widget(self._results_box)
        # layout.add_widget(Text("File name:", "filename"))
        # layout.add_widget(Text("Contact:", "contact"))
        #layout.add_widget(TextBox(
        #    Widget.FILL_FRAME, "Notes:", "notes", as_string=True, line_wrap=True))
        button_layout = Layout([1, 1, 1])
        self.add_layout(button_layout)
        button_layout.add_widget(Button("Display all contacts", self._display_all), 0)
        button_layout.add_widget(Button("Find contacts born in June", self._find_june), 1)
        button_layout.add_widget(Button("Cancel", self._cancel), 2)
        self.fix()
        #self.reset()

    def process_event(self, event):
        if hasattr(event, "key_code") and event.key_code == Screen.KEY_ESCAPE:
            raise NextScene("Main")
        return super().process_event(event)
    def _display_all(self):
        if self._model.conn is None:
            return
        if not self._model.vCardFiles:
            self.show_message("No vCard files available.")
            return
        cursor = self._model.conn.cursor()
        cursor.autocommit = True
        cursor.execute("Select CONTACT.contact_id, CONTACT.name, CONTACT.birthday, CONTACT.anniversary, FILE.file_name from CONTACT JOIN FILE ON CONTACT.file_id = FILE.file_id ORDER BY CONTACT.name")
        results = cursor.fetchall()
        if results is None:
            self.show_message("No contacts found")
            return
        # fullEntry = ""
        # for row in result:
        #     name, birthday, anniversary, filename = row
        #     entry = f"Name: {name}, Birthday: {birthday}, Anniversary: {anniversary}, Filename: {filename}"
        #     fullEntry += entry + "\n"
        # self.data = {
        #     "query": fullEntry
        # }
        display_data = []
        header = f"{'id'}|{'Name':<15} | {'Filename':<17} |{'Birthday':<10}|{'Anniv.':<10}"
        divider = "-" * len(header)
        display_data.append((header, 0))
        display_data.append((divider, 1))

        for i, row in enumerate(results, start=2):
            id, name, birthday, anniversary, filename = row
            #print(name, birthday, anniversary, filename)
            formatted = f"{id}|{name:<15} | {filename:<17} |{str(birthday or 'N/A'):<10} |{str(anniversary or 'N/A'):<10}"
            display_data.append((formatted, i))

        # Update the ListBox with new options
        self._results_box.options = display_data
        self._results_box.value = 0  # Select the first row
        self.reset()
        cursor.execute("SELECT COUNT(*) FROM FILE")
        n1 = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM CONTACT")
        n2 = cursor.fetchone()[0]

        self.show_message(f"Database has {n1} files and {n2} contacts")


    def _find_june(self):
        if self._model.conn is None:
            return
        if not self._model.vCardFiles:
            self.show_message("No vCard files available.")
            return
        cursor = self._model.conn.cursor()
        cursor.autocommit = True
        # sorted by age. You can compute the age as the different between the birth 
        #date and the time that the vCard file containing that individual's record was last modified.
        # The function DATEDIFF() will return the difference in days between two DATETIMES. You can convert this value to years by dividing it by 365.
        cursor.execute("SELECT name, birthday FROM CONTACT JOIN FILE ON CONTACT.file_id = FILE.file_id WHERE MONTH(birthday) = 6 ORDER BY DATEDIFF(FILE.last_modified, birthday)/365")
        results = cursor.fetchall()
        if results is None:
            self.show_message("No contacts found")
            return
        display_data = []
        header = f"{'Name':<15} | {str('birthday'):<10}"
        divider = "-" * len(header)
        display_data.append((header, 0))
        display_data.append((divider, 1))
        for i, row in enumerate(results, start=2):
            name, birthday = row
           # print (name, birthday)
            formatted = f"{name:<15} | {str(birthday or 'N/A'):<10}"
            display_data.append((formatted, i))
        self._results_box.options = display_data
        self._results_box.value = 0
        self.reset()
        cursor.execute("SELECT COUNT(*) FROM FILE")
        n1 = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM CONTACT")
        n2 = cursor.fetchone()[0]
        self.show_message(f"Database has {n1} files and {n2} contacts")

    def show_message(self, message):
        self.scene.add_effect(PopUpDialog(self.screen, message, ["OK"]))
    def reset(self):
        # Do standard reset to clear out form, then populate with new data.
        
        super(DataBaseView, self).reset()
      #  self.show_message ("reset")


    



    @staticmethod
    def _cancel():
        raise NextScene("Main")














class LoginView(Frame):
    def __init__(self, screen, model):
        super(LoginView, self).__init__(screen,
                                        screen.height * 2 // 3,
                                        screen.width * 2 // 3,
                                        hover_focus=True,
                                        can_scroll=False,
                                        title="Login to Database")

        # Save off the model that accesses the database.
        self._model = model

        # First Layout: Fields
        layout = Layout([100], fill_frame=True)
        self.add_layout(layout)
        layout.add_widget(Text("Username:", "username"))
        layout.add_widget(Text("Password:", "password", hide_char="*"))  # Hide password
        layout.add_widget(Text("Database:", "database"))

        # Second Layout: Buttons
        layout2 = Layout([1, 1])
        self.add_layout(layout2)
        layout2.add_widget(Button("Login", self._ok), 0)
        layout2.add_widget(Button("Cancel", self._cancel), 1)

        self.fix()
    def process_event(self, event):
        if hasattr(event, "key_code") and event.key_code == Screen.KEY_ESCAPE:
            raise NextScene("Main")
        return super().process_event(event)

    def _ok(self):
        self.save()
        username = self.data["username"]
        password = self.data["password"]
        database = self.data["database"]

        if not username or not password or not database:
            self.show_message("All fields must be completed")
            return
        
        try:
            self._model.conn =  mysql.connector.connect(host="dursley.socs.uoguelph.ca", 
    database=database,user=username, password=password)
            self.show_message("Login successful")
            if self._model.conn:
                global contacts
                contacts = ContactModel(self._model.conn)  
        except mysql.connector.Error as err:
            
            self.show_message(f"wwError: {err}")
            return
        except Exception as e:
           #self.show_message(f"Error: {e}")
           self.show_message(f"Error: {repr(e)}")  
        raise NextScene("Main")

    def show_message(self, message):
        self.scene.add_effect(PopUpDialog(self.screen, message, ["OK"]))

    @staticmethod
    def _cancel():
         raise NextScene("Main")








def demo(screen, scene):
    #global contacts
    scenes = [
        Scene([LoginView(screen, contacts) ], -1, name="Login"),
        Scene([ListView(screen, contacts)], -1, name="Main"),
        Scene([ContactView(screen, contacts)], -1, name="Edit Contact"),
        Scene([CreateView(screen, contacts)], -1, name="create card"),
        Scene([DataBaseView(screen, contacts)], -1, name="DB queries")
    ]

    screen.play(scenes, stop_on_resize=True, start_scene=scene, allow_int=True)


contacts = ContactModel()

last_scene = None
while True:
    try:
        Screen.wrapper(demo, catch_interrupt=True, arguments=[last_scene])
        sys.exit(0)
    except ResizeScreenError as e:
        last_scene = e.scene