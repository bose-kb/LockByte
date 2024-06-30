# ====================================================================
# This file is part of LockByte.
# LockByte is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, version 3 of the License.
# LockByte is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with LockByte. If not, see <https://www.gnu.org/licenses/>.
# ====================================================================

from PIL import Image, ImageTk
import darkdetect
import customtkinter as ctk
from argon2 import exceptions as argon2exceptions

from tkinter import filedialog, ttk, Menu
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from sys import exc_info, argv
from os import walk, unlink, path as ospath, remove as osremove
from platform import system
from fnmatch import fnmatch
import webbrowser

from lockbyte.lock_unlock import LockByteUser
# from lock_unlock import LockByteUser


# class to raise custom exception
class EmptyFolderError(Exception):
    '''
    Extends standard exception class to provide custom exception for empty folder errors.
    '''
    pass


class App(ctk.CTkFrame):
    '''
    Class to build customtkinter UI for the LockByte App
    '''

    def __init__(self, root) -> None:

        super().__init__(root)
        style = ttk.Style()

        # styling options
        if darkdetect.isDark():
            self.colour1 = "#0078F0"  # button colour
            self.colour2 = "#565B5E"  # border colour
            self.colour3 = "#4A4D50"  # progressbar inactive
            self.colour4 = "#2B2B2B"  # frame
            self.colour5 = "#1D1E1E"  # textbox
            self.colour_root = "#242424"
            root.configure(fg_color=self.colour_root)
            ctk.set_appearance_mode("dark")
            style.theme_create('style', parent='alt',
                               settings={'TLabelframe': {'configure':
                                                         {'background': self.colour4,
                                                          'relief': 'solid',  # has to be 'solid' to color
                                                          'bordercolor': self.colour1,
                                                          'borderwidth': 1}},
                                         'TLabelframe.Label': {'configure':
                                                               {'foreground': 'white',
                                                                'background': self.colour4,
                                                                'font': ("Aileron", 8)}}})
        else:
            self.colour1 = "#36c3eb"
            self.colour2 = "#979DA2"
            self.colour3 = "#C8C8C8"
            self.colour4 = "#E7E6EC"
            self.colour5 = "#F9F9FA"
            self.colour_root = "#FFFFFF"
            root.configure(fg_color=self.colour_root)
            ctk.set_appearance_mode("light")
            style.theme_create('style', parent='alt',
                               settings={'TLabelframe': {'configure':
                                                         {'background': self.colour4,
                                                          'relief': 'solid',  # has to be 'solid' to color
                                                          'bordercolor': self.colour1,
                                                          'borderwidth': 1}},
                                         'TLabelframe.Label': {'configure':
                                                               {'foreground': 'black',
                                                                'background': self.colour4,
                                                                'font': ("Aileron", 8)}}})
        style.theme_use('style')

        self.font_heading = "Work Sans ExtraLight"
        self.font_text_normal = "Aileron"
        self.font_text_logs = "Office Code Pro"
        self.font_button = "Aileron Bold"

        self.main_frame = self
        self.second_frame = ctk.CTkFrame(root)
        self.load_main_widgets()  # load all widgets
        self.index = 0  # index number for frames
        self.cancel_event = Event()
        self.user_tips_write_ready_event = Event()
        self.user_tips_write_ready_event.set()

        # configure widget(s) behaviour on keypress
        self.passw_text.bind("<Any-KeyPress>", lambda event,
                             flg=0: self.delayed_action_call(event, flg))
        self.source_file_text.bind(
            "<Any-KeyPress>", lambda event, flg=1: self.delayed_action_call(event, flg))
        self.source_folder_text.bind(
            "<Any-KeyPress>", lambda event, flg=2: self.delayed_action_call(event, flg))
        self.user_tips.bind("<1>", lambda event: self.user_tips.focus_set())
        self.bottom_label.bind(
            "<Button-1>", lambda e: webbrowser.open_new("https://github.com/bose-kb/LockByte"))

        # declare multi-threading variables
        global pool, jobs
        pool = None
        jobs = []

    # function to call all other widgets creation functions
    def load_main_widgets(self):
        '''
        Function to call all other widgets creation functions
        '''
        self.create_home_screen()
        self.create_action_screen()
        self.main_frame.pack(fill=ctk.BOTH, expand=True, padx=12, pady=12)
        self.second_frame.pack(fill=ctk.BOTH, expand=True, padx=12, pady=12)
        self.frame_list = [self.main_frame, self.second_frame]
        self.frame_list[1].forget()

    # function to open filedialog for file
    def browse_file(self):
        '''
        Function to open filedialog for file picking
        '''
        self.source_file_text.delete(0, ctk.END)
        if self.action_button.cget("text") == "Encrypt":
            file_path = filedialog.askopenfilename(
                initialdir="", title="Select a file")
        else:
            file_path = filedialog.askopenfilename(filetypes=(("LOCKBYTE files", "*.lockbyte"), ("All files", "*")),
                                                   initialdir="", title="Select a file")
        self.source_file_text.insert(0, file_path)
        self.source_folder_text.delete(0, ctk.END)
        self.disable_folder_pick()

    # function to open filedialog for folder
    def browse_folder(self):
        '''
        Function to open filedialog for folder picking
        '''
        self.source_folder_text.delete(0, ctk.END)
        if self.action_button.cget("text") == "Encrypt":
            folder_path = filedialog.askdirectory(
                initialdir="", title="Select a folder")
        else:
            folder_path = filedialog.askdirectory(
                initialdir="", title="Select a folder")
        self.source_folder_text.insert(0, folder_path)
        self.source_file_text.delete(0, ctk.END)
        self.disable_file_pick()

    # function to disable file picker
    def disable_file_pick(self):
        '''
        Function to disable file picker when folder picker is in use
        '''
        self.check_pass()
        if len(self.source_folder_location.get().strip()) < 1:
            self.source_file_text.configure(state="normal")
            if self.browse_file_button.cget('state') != "normal":
                self.browse_file_button.configure(state="normal")
                self.browse_file_button.configure(fg_color=self.colour1)
            self.source_file_text.configure(border_color=self.colour2)
            self.source_folder_text.configure(border_color=self.colour2)
        else:
            self.source_file_text.configure(state="disabled")
            if self.browse_file_button.cget('state') != "disabled":
                self.browse_file_button.configure(state="disabled")
                self.browse_file_button.configure(fg_color=self.colour2)
            self.source_folder_text.configure(border_color=self.colour1)
            self.source_file_text.configure(border_color="")

    # function to disable folder picker
    def disable_folder_pick(self):
        '''
        Function to disable folder picker when file picker is in use
        '''
        self.check_pass()
        self.delayed_action_call(0)
        if len(self.source_file_location.get().strip()) < 1:
            self.source_folder_text.configure(state="normal")
            if self.browse_folder_button.cget('state') != "normal":
                self.browse_folder_button.configure(state="normal")
                self.browse_folder_button.configure(fg_color=self.colour1)
            self.source_folder_text.configure(border_color=self.colour2)
            self.source_file_text.configure(border_color=self.colour2)
        else:
            self.source_folder_text.configure(state="disabled")
            if self.browse_folder_button.cget('state') != "disabled":
                self.browse_folder_button.configure(state="disabled")
                self.browse_folder_button.configure(fg_color=self.colour2)
            self.source_file_text.configure(border_color=self.colour1)
            self.source_folder_text.configure(border_color="")

    # function to create new thread(s) for parallel execution of encryption/decryption process
    def start_thread_pool(self, mode: str):
        '''
        Function to spawn threads for parallel execution of encryption/decryption taks

        :param mode: indicates mode choice by user, whether 'file' or 'folder' picker used
        '''
        self.cancel_button.configure(text="Abort")  # enable abort button
        self.cancel_button.configure(
            fg_color=("#F62A43", "#EF1214"))  # configure abort button
        self.cancel_button.configure(hover_color=(
            '#961827', '#7D090A'))  # reconfigure exit button
        self.back_button.configure(state="disabled")  # disable back button
        self.action_button.configure(state="disabled")  # disable action button
        self.passw_text.configure(state="disabled")  # disable password entry
        self.passw_text.configure(border_color=self.colour2)
        self.progress_bar.configure(
            progress_color=self.colour1)  # update progressbar
        global pool, jobs

        # create a pool of threads for parallel execution
        pool = ThreadPoolExecutor(max_workers=2)

        try:
            # check file/folder option choice
            if mode == "file":
                # disable file picker
                self.source_file_text.configure(state="disabled")
                self.source_file_text.configure(border_color=self.colour2)
                self.browse_file_button.configure(state="disabled")
                self.browse_file_button.configure(fg_color=self.colour2)
                file_path = self.source_file_location.get().strip()
                if self.action_button.cget("text") == "Encrypt":
                    self.progress_bar.start()
                    # add job to pool
                    jobs = [pool.submit(
                        self.begin_encryption, file_path, self.cancel_event)]
                    # update progressbar
                    self.after(200, self.check_thread_pool)
                else:
                    self.progress_bar.start()
                    # add job to pool
                    jobs = [pool.submit(
                        self.begin_decryption, file_path, self.cancel_event)]
                    # update progressbar
                    self.after(200, self.check_thread_pool)

            elif mode == "folder":
                # disable folder picker
                self.source_folder_text.configure(state="disabled")
                self.source_folder_text.configure(border_color=self.colour2)
                self.browse_folder_button.configure(state="disabled")
                self.browse_folder_button.configure(fg_color=self.colour2)
                folder_path = self.source_folder_location.get().strip()
                extension = "*.lockbyte"
                jobs = []

                if self.action_button.cget("text") == "Encrypt":
                    self.progress_bar.start()
                    # search given folder and sub folders
                    for path, subdirs, files in walk(folder_path):
                        for name in files:
                            jobs.append(pool.submit(
                                # add job to pool
                                self.begin_encryption, ospath.join(path, name), self.cancel_event))
                    self.update_idletasks()
                    # update progressbar
                    self.after(200, self.check_thread_pool)
                    if len(jobs) == 0:
                        raise EmptyFolderError(
                            "Folder is empty or invalid folder path provided")
                else:
                    self.progress_bar.start()
                    # search given folder and sub folders
                    for path, subdirs, files in walk(folder_path):
                        for name in files:
                            if fnmatch(name, extension):
                                jobs.append(pool.submit(
                                    # add job to pool
                                    self.begin_decryption, ospath.join(path, name), self.cancel_event))
                    self.update_idletasks()
                    # update progressbar
                    self.after(200, self.check_thread_pool)
                    if len(jobs) == 0:
                        raise EmptyFolderError(
                            "Folder is empty or no lockbyte files were found")

        except EmptyFolderError as e:  # handle empty folder condition
            self.update_user_tips(
                "-- Empty folder error: {0}\n".format(e), self.user_tips_write_ready_event)
        except:  # handle other exceptions
            self.update_user_tips(
                "-- Unexpected error: {0}\n".format(exc_info()[1]), self.user_tips_write_ready_event)
            raise

    # function to handle encryption
    def begin_encryption(self, file_path: str, cancel_event: Event):
        '''
        Function to handle encryption process

        :param file_path: path to file to be encrypted
        :param cancel_event: threading.Event object to signal cancellation of operation
        '''
        user = LockByteUser(self.user_passw.get().strip())
        # encryption process
        try:
            self.update_user_tips(
                "-- Reading File: {0}\n".format(file_path), self.user_tips_write_ready_event)
            with open(file_path, "rb") as file:
                self.update_user_tips(
                    "-- Encrypting..\n", self.user_tips_write_ready_event)
                if user.validate_and_generate(1):
                    if cancel_event.is_set():
                        return
                    user.encrypt(file=file, file_path=file_path)
            if self.keep_files_switch_val.get() == "off" and ospath.isfile(file_path):
                osremove(file_path)
            self.update_user_tips(
                "-- Encrypted: {0}\n".format(file_path), self.user_tips_write_ready_event)

        except FileNotFoundError:
            self.update_user_tips(
                "-- File error: {0} not found\n".format(file_path), self.user_tips_write_ready_event)
        except IOError as e:
            self.update_user_tips(
                "-- I/O error({0}): {1}\n".format(e.errno, e.strerror), self.user_tips_write_ready_event)
        except ValueError as ve:  # handle low memory case
            if "Error 2 while running scrypt" in getattr(ve, 'message', str(ve)):
                self.update_user_tips(
                    "-- Memory error: Not enough memory available\n", self.user_tips_write_ready_event)
            else:
                self.update_user_tips(
                    "-- Unexpected error: {0}\n".format(exc_info()[1]), self.user_tips_write_ready_event)
        except:  # handle other exceptions
            self.update_user_tips(
                "-- Unexpected error: {0}\n".format(exc_info()[1]), self.user_tips_write_ready_event)

    # function to handle decryption
    def begin_decryption(self, file_path: str, cancel_event: Event):
        '''
        Function to handle decryption process

        :param file_path: path to file to be decrypted
        :param cancel_event: threading.Event object to signal cancellation of operation
        '''
        user = LockByteUser(self.user_passw.get().strip())
        # decryption process
        try:
            self.update_user_tips(
                "-- Reading File: {0}\n".format(file_path), self.user_tips_write_ready_event)
            with open(file_path, "rb") as file:
                self.update_user_tips(
                    "-- Decrypting..\n", self.user_tips_write_ready_event)
                file_path_new = user.decrypt(file=file, file_path=file_path)
                if cancel_event.is_set():
                    if ospath.isfile(file_path_new):
                        osremove(file_path_new)
                    return
            self.update_user_tips(
                "-- Decrypted: {0}\n".format(file_path), self.user_tips_write_ready_event)
        except FileNotFoundError:
            self.update_user_tips(
                "-- File error: {0} not found\n".format(file_path), self.user_tips_write_ready_event)
        except IOError as e:
            self.update_user_tips(
                "-- I/O error({0}): {1}\n".format(e.errno, e.strerror), self.user_tips_write_ready_event)
        except argon2exceptions.InvalidHashError:  # handle corrupt/ non-lockbyte files
            self.update_user_tips(
                "-- File error: File chosen is corrupt or of incorrect type\n", self.user_tips_write_ready_event)
        except argon2exceptions.VerifyMismatchError:  # handle incorrect password
            self.update_user_tips(
                "-- Authentication error: Password entered is incorrect\n", self.user_tips_write_ready_event)
        except ValueError as ve:  # handle low memory case
            if "Error 2 while running scrypt" in getattr(ve, 'message', str(ve)):
                self.update_user_tips(
                    "-- Memory error: Not enough memory available\n", self.user_tips_write_ready_event)
            elif not self.cancel_event.is_set():
                self.update_user_tips(
                    "-- Unexpected error occured\n", self.user_tips_write_ready_event)
        except:  # handle other exceptions
            self.update_user_tips(
                "-- Unexpected error: {0}\n".format(exc_info()[1]), self.user_tips_write_ready_event)

    # check status of thread and update progressbar
    def check_thread_pool(self):
        '''
        Function to monitor status of worker threads spawned

        :param cancel_operation: flag variable to indicate if cancel request was made
        '''
        for job in jobs:
            if job.done():
                jobs.remove(job)  # remove completed job from jobs list
            else:
                break
        if len(jobs) > 0:
            self.after(200, self.check_thread_pool)
            self.update_idletasks()
        else:
            # update progressbar
            self.progress_bar.stop()
            self.progress_bar.configure(progress_color=self.colour3)
            self.progress_bar.set(0)

            self.back_button.configure(
                state="normal")  # enable back button
            self.cancel_button.configure(
                state="normal")  # enable back button
            self.action_button.configure(
                state="normal")  # enable action button
            self.passw_text.configure(
                state="normal")  # enable password entry
            self.passw_text.configure(border_color=self.colour1)
            # enable file/folder pickers
            self.disable_file_pick()
            self.disable_folder_pick()
            self.cancel_button.configure(
                text="Exit")  # reconfigure exit button
            self.cancel_button.configure(
                fg_color=self.colour1)  # reconfigure exit button
            self.cancel_button.configure(
                hover_color=('#36719F', '#144870'))  # reconfigure exit button
            # close thread pool
            if not self.cancel_event.is_set():
                pool.shutdown()
            self.cancel_event.clear()  # clear cancel event
            self.update_user_tips(
                "-- Done.\n", self.user_tips_write_ready_event)

    # cancel thread(s) operation if cancel button pressed or exit operation if exit button pressed
    def cancel_all_threads(self):
        '''
        Function to initiate cancel/application exit request and terminate worker threads
        '''
        if self.cancel_button.cget('text') == "Exit":
            app_root.destroy()
        else:
            self.cancel_button.configure(state="disabled")
            self.cancel_event.set()
            self.update_user_tips(
                "-- Aborting..\n", self.user_tips_write_ready_event)
            pool.shutdown(wait=False, cancel_futures=True)
            self.progress_bar.configure(progress_color=("#F62A43", "#EF1214"))
            if self.action_button.cget('text') == "Decrypt":
                self.update_user_tips(
                    "-- Rolling back changes..\n", self.user_tips_write_ready_event)
            self.check_thread_pool

    # add 1ms delay for Entry widgets to update
    def delayed_action_call(self, event=None, flg=None):
        '''
        Function to add delay between updation and extraction of content from entry widgets

        :param event: events binded to widgets
        :param flg: flag to indicate action to be performed with delay
        '''
        if flg == 0:
            self.after(1, self.check_pass)
        elif flg == 1:
            self.after(1, self.disable_folder_pick)
        elif flg == 2:
            self.after(1, self.disable_file_pick)
        elif flg == 3:
            self.after(1, self.check_confirm_pass)

    # check if entered password is of required length
    def check_pass(self):
        '''
        Function to check if password meets necessary criteria
        '''
        if len(self.user_passw.get().strip()) >= 6:
            self.passw_text.configure(border_color=self.colour1)
            if len(self.source_folder_location.get().strip()) or len(self.source_file_location.get().strip()):
                self.action_button.configure(state="normal")
            else:
                self.action_button.configure(state="disabled")
        else:
            self.action_button.configure(state="disabled")
            self.passw_text.configure(border_color=self.colour2)

    # fuction to update user-tips
    def update_user_tips(self, message: str, user_tips_write_ready_event: Event):
        '''
        Function to write messages to user-tips box

        :param message: message to be writtn to user-tips box
        :param user_tips_write_ready_event: threading.Event object used to indicate text widget ready state
        '''
        user_tips_write_ready_event.wait(timeout=0.5)
        user_tips_write_ready_event.clear()
        self.user_tips.configure(state="normal")
        self.user_tips.insert(
            ctk.END, message)
        self.user_tips.configure(state="disabled")
        user_tips_write_ready_event.set()

    # function to clear widgets when going to previous page
    def on_click_back(self, window_change_req: int = 0):
        '''
        Function to clear all widget contents when user goes to previous page

        :param window_change_req: 0 = window change required, 1 = not required 
        '''
        self.user_tips.configure(state="normal")
        self.user_tips.delete('1.0', ctk.END)
        self.user_tips.configure(state="disabled")
        self.source_file_text.delete(0, ctk.END)
        self.source_folder_text.delete(0, ctk.END)
        self.passw_text.delete(0, ctk.END)
        self.check_pass()
        self.disable_file_pick()
        self.disable_folder_pick()
        if window_change_req == 0:
            self.change_window(mode=-1)

    # function to create homepage
    def create_home_screen(self):
        '''
        Function to create home page of the app
        '''
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure((0, 1), weight=1)
        self.main_frame.configure(fg_color=self.colour4)

        self.head_label = ctk.CTkLabel(
            self.main_frame,
            text="LockByte",
            font=(self.font_heading, 60),
        )
        self.head_label.grid(column=0, row=0, rowspan=2,
                             sticky=ctk.N, pady=(50, 0))

        self.button_encrypt = ctk.CTkButton(
            self.main_frame,
            fg_color=self.colour1,
            text_color=("black", "white"),
            height=35,
            width=150,
            font=(self.font_button, 15),
            image=ctk.CTkImage(light_image=Image.open(ospath.join(curr_path,
                                                                  "assets/icons/lock-light-mode.png")),
                               dark_image=Image.open(ospath.join(curr_path,
                                                                 "assets/icons/lock-dark-mode.png")),
                               size=(15, 15)),
            compound="right",
            text="Encrypt",
            command=lambda: self.change_window(mode=1, new=" New ", width=222)
        )
        self.button_encrypt.grid(
            column=0, row=0, rowspan=2, sticky=ctk.N, pady=(200, 0))

        self.button_decrypt = ctk.CTkButton(
            self.main_frame,
            fg_color=self.colour1,
            text_color=("black", "white"),
            height=35,
            width=150,
            font=(self.font_button, 15),
            image=ctk.CTkImage(light_image=Image.open(ospath.join(curr_path,
                                                                  "assets/icons/unlock-light-mode.png")),
                               dark_image=Image.open(ospath.join(curr_path,
                                                                 "assets/icons/unlock-dark-mode.png")),
                               size=(15, 15)),
            compound="right",
            text="Decrypt",
            command=lambda: self.change_window(mode=0)
        )
        self.button_decrypt.grid(column=0, row=1, sticky=ctk.N, pady=(100, 0))

        self.bottom_label = ctk.CTkLabel(
            self.main_frame,
            text="Created & maintained by bosekb",
            text_color=self.colour2,
            font=(self.font_text_normal, 12),
            cursor="hand2"
        )
        self.bottom_label.grid(column=0, row=1,
                               sticky=ctk.S, pady=(0, 25))

        self.info_button = ctk.CTkButton(
            self.main_frame,
            fg_color=(self.colour3, self.colour2),
            hover_color=(self.colour2, self.colour3),
            text_color=("black", "white"),
            height=25,
            width=25,
            image=ctk.CTkImage(light_image=Image.open(ospath.join(curr_path,
                                                                  "assets/icons/info-light-mode.png")),
                               dark_image=Image.open(ospath.join(curr_path,
                                                                 "assets/icons/info-dark-mode.png")),
                               size=(13, 13)),
            text="",
            command=self.create_info_window
        )
        self.info_button.grid(
            column=0, row=0, sticky=ctk.NE, padx=15, pady=(15, 0))

    # function to create action page
    def create_action_screen(self):
        '''
        Function to create action page of the app
        '''
        # Configure grid layout for action page
        self.second_frame.columnconfigure((0, 1), weight=1)
        self.second_frame.rowconfigure((0, 1, 2, 3, 4), weight=1)
        self.second_frame.configure(fg_color=self.colour4)

        # configure label frame
        self.label_frame = ttk.Labelframe(
            self.second_frame,
            text="   Pick a file or folder   ",
            labelanchor='n'
        )

        self.label_frame.grid(row=0, rowspan=2, column=0, columnspan=2,
                              sticky=ctk.NSEW, padx=10, pady=10)
        self.label_frame.rowconfigure((0, 1), weight=1)
        self.label_frame.columnconfigure(0, weight=3)
        self.label_frame.columnconfigure(1, weight=1)

        # configure label for file picker
        self.source_file_label = ctk.CTkLabel(
            self.label_frame,
            height=25,
            text="File Path :",
            font=(self.font_text_normal, 13)

        )
        self.source_file_label.grid(row=0, column=0, columnspan=2,
                                    sticky=ctk.NW, padx=10, pady=(15, 0))

        # configure input-box for file picker
        self.source_file_location = ctk.StringVar()
        self.source_file_text = ctk.CTkEntry(
            self.label_frame,
            width=232,
            textvariable=self.source_file_location,
            font=(self.font_text_logs, 13),
        )
        self.source_file_text.grid(row=0, column=0, columnspan=2,
                                   sticky=ctk.NE, padx=50, pady=(15, 0))

        # configure button file picker
        self.browse_file_button = ctk.CTkButton(
            self.label_frame,
            fg_color=self.colour1,
            height=25,
            width=30,
            image=ctk.CTkImage(light_image=Image.open(ospath.join(curr_path,
                                                                  "assets/icons/file-light-mode.png")),
                               dark_image=Image.open(ospath.join(curr_path,
                                                                 "assets/icons/file-dark-mode.png")),
                               size=(16, 16)),
            text="",
            command=self.browse_file
        )
        self.browse_file_button.grid(
            row=0, column=1, sticky=ctk.NE, padx=10, pady=(15, 0))

        # configure label folder picker
        self.source_folder_label = ctk.CTkLabel(
            self.label_frame,
            height=25,
            text="Folder Path :",
            font=(self.font_text_normal, 13)

        )
        self.source_folder_label.grid(row=1, column=0, columnspan=2,
                                      sticky=ctk.NW, padx=10, pady=(30, 0))

        # configure input-box for folder picker
        self.source_folder_location = ctk.StringVar()
        self.source_folder_text = ctk.CTkEntry(
            self.label_frame,
            width=216,
            textvariable=self.source_folder_location,
            font=(self.font_text_logs, 13),
        )
        self.source_folder_text.grid(row=1, column=0, columnspan=2,
                                     sticky=ctk.NE, padx=50, pady=(30, 0))

        # configure button for folder picker
        self.browse_folder_button = ctk.CTkButton(
            self.label_frame,
            fg_color=self.colour1,
            height=25,
            width=30,
            image=ctk.CTkImage(light_image=Image.open(ospath.join(curr_path,
                                                                  "assets/icons/folder-light-mode.png")),
                               dark_image=Image.open(ospath.join(curr_path,
                                                                 "assets/icons/folder-dark-mode.png")),
                               size=(16, 16)),
            text="",
            command=self.browse_folder
        )
        self.browse_folder_button.grid(
            row=1, column=1, sticky=ctk.NE, padx=10, pady=(30, 0))

        # configure label for password entry
        self.passw_label = ctk.CTkLabel(
            self.second_frame,
            height=25,
            text="Enter Password :",
            font=(self.font_text_normal, 13)

        )
        self.passw_label.grid(row=2, column=0, columnspan=2,
                              sticky=ctk.NW, padx=10, pady=20)

        # configure input-box for password entry
        self.user_passw = ctk.StringVar()
        self.passw_text = ctk.CTkEntry(
            self.second_frame,
            show="\u2022",
            textvariable=self.user_passw,
            font=(self.font_text_normal, 13)
        )
        self.passw_text.grid(row=2, column=0, columnspan=2,
                             sticky=ctk.NE, padx=10, pady=20)

        # configure progressbar
        self.progress_bar = ctk.CTkProgressBar(
            self.second_frame,
            orientation="horizontal",
            mode="indeterminate",
            fg_color=self.colour3,
            progress_color=self.colour3,
            height=18,
        )
        self.progress_bar.grid(row=2, rowspan=2, column=0, columnspan=2,
                               sticky=ctk.EW, padx=10, pady=(0, 0))

        # configure user tips box
        self.user_tips = ctk.CTkTextbox(
            self.second_frame,
            height=130,
            state="disabled",
            font=(self.font_text_logs, 12),
            fg_color=self.colour5
        )
        self.user_tips.grid(row=3, rowspan=2, column=0, columnspan=2,
                            sticky=ctk.EW, padx=10, pady=(0, 40))

        # add navigation buttons for back, encryption/decryption & exit/cancel
        self.back_button = ctk.CTkButton(
            self.second_frame,
            fg_color=self.colour1,
            width=70,
            text="Back",
            font=(self.font_button, 11),
            text_color=("black", "white"),
            image=ctk.CTkImage(light_image=Image.open(ospath.join(curr_path,
                                                                  "assets/icons/back-light-mode.png")),
                               dark_image=Image.open(ospath.join(curr_path,
                                                                 "assets/icons/back-dark-mode.png")),
                               size=(11, 11)),
            compound="left",
            anchor="center",
            command=self.on_click_back
        )
        self.back_button.grid(row=4, column=0, sticky=ctk.SW, padx=10, pady=15)

        self.action_button = ctk.CTkButton(
            self.second_frame,
            fg_color=self.colour1,
            width=70,
            text="Action",
            font=(self.font_button, 11),
            state="disabled",
            text_color=("black", "white"),
            command=self.create_confirmation_window
        )
        self.action_button.grid(row=4,
                                column=1, sticky=ctk.SE, padx=90, pady=15)

        self.cancel_button = ctk.CTkButton(
            self.second_frame,
            fg_color=self.colour1,
            width=70,
            text="Exit",
            font=(self.font_button, 11),
            text_color=("black", "white"),
            command=self.cancel_all_threads
        )
        self.cancel_button.grid(row=4,
                                column=1, sticky=ctk.SE, padx=10, pady=15)

    # function to swap between windows & change window content
    def change_window(self, mode: int, new=" ", width=251):
        '''
        Function to switch between pages of the app

        :param mode: mode (Encryption/Decryption) selected by the user
        :param new: optional text to be put in the password entry label
        :param width: width of the password entry box
        '''
        self.frame_list[self.index].forget()
        self.index = (self.index + 1) % len(self.frame_list)
        self.passw_label.configure(text="Enter"+new+"Password :")
        self.passw_text.configure(width=width)
        if mode == 0:  # decrypt button pressed
            self.action_button.configure(text="Decrypt")
        elif mode == 1:  # encrypt button pressed
            self.action_button.configure(text="Encrypt")
        self.frame_list[self.index].tkraise()  # raise other page
        self.frame_list[self.index].pack(
            fill=ctk.BOTH, expand=True, padx=12, pady=12)  # re-pack other page
        self.frame_list[self.index].update_idletasks()

    # function to create info page
    def create_info_window(self):
        '''
        Function to create application info dialog
        '''
        # configure info window
        arguments = {
            'class': "LockByte",
            'master': self
        }
        info_window = ctk.CTkToplevel(**arguments)
        x = self.master.winfo_x()
        y = self.master.winfo_y()
        info_window.geometry(
            "%dx%d+%d+%d" % (400, 400, x + 140, y + 50))
        info_window.title("About")
        info_window.minsize(400, 400)
        info_window.maxsize(400, 400)
        info_window.configure(fg_color=self.colour_root)

        if system() == 'Windows':
            info_window.after(200, lambda: info_window.iconbitmap(
                ospath.join(curr_path, "assets/icons/main_icon.ico")))
        elif system() == 'Darwin':
            info_window.after(200, lambda: info_window.iconbitmap(
                ospath.join("/", "Applications/LockByte.app")))
            info_window.resizable(width=False, height=False)
        else:
            info_window.after(
                200, lambda: info_window.iconphoto(True, icon_photo))
            info_window.resizable(width=False, height=False)

        # configure info frame
        info_frame = ctk.CTkFrame(master=info_window)
        info_frame.rowconfigure((0), weight=1)
        info_frame.columnconfigure((0), weight=1)
        info_frame.configure(fg_color=self.colour4)
        info_frame.pack(fill=ctk.BOTH, expand=True, padx=12, pady=12)

        # configure info text box
        info_text_box = ctk.CTkTextbox(
            info_frame,
            fg_color=info_frame._fg_color,
            wrap='word',
            activate_scrollbars=False,
            font=(self.font_text_normal, 14),
        )
        info_text_box.grid(column=0, row=0, sticky=ctk.NSEW, padx=5, pady=5)

        info_text = "LockByte\nVersion 1.0.0\nCopyright © 2024 Krishnendu Bose.\n-----------------------------------------------------\nLockByte is an easy to use, open-source file encryption application designed to cater to the needs of individuals who prioritize data security and want to protect their data without dealing with complex software.\n\nLockByte is free software. You can redistribute it and/or modify it under the terms of the GNU General Public License (version 3) as published by the Free Software Foundation.\n\nFonts used are under the SIL Open Font License (version 1.1) & Creative Commons CC0 License (version 1.0).\n\nIcons used are from Icons8."
        info_text_box.insert(ctk.END, info_text)
        info_text_box.configure(state="disabled")

        # configure done button
        done_button = ctk.CTkButton(
            info_frame,
            fg_color=self.colour1,
            width=55,
            height=20,
            text="",
            image=ctk.CTkImage(light_image=Image.open(ospath.join(curr_path,
                                                                  "assets/icons/done-light-mode.png")),
                               dark_image=Image.open(ospath.join(curr_path,
                                                                 "assets/icons/done-dark-mode.png")),
                               size=(18, 18)),
            command=info_window.destroy
        )
        done_button.grid(
            row=0, column=0, sticky=ctk.SE, padx=12, pady=12)

        info_window.grab_set()

    # function to create confirmation dialog
    def create_confirmation_window(self):
        '''
        Function to create password confirmation dialog
        '''
        if self.action_button.cget("text") == "Decrypt":
            if len(self.source_file_location.get().strip()) > 0:
                self.start_thread_pool("file")
            else:
                self.start_thread_pool("folder")
        else:
            # configure confirmation window
            arguments = {
                'class': "LockByte",
                'master': self
            }
            self.confirmation_window = ctk.CTkToplevel(**arguments)
            x = self.master.winfo_x()
            y = self.master.winfo_y()
            self.confirmation_window.geometry(
                "%dx%d+%d+%d" % (300, 230, x + 140, y + 50))
            self.confirmation_window.title("Confirm Password")
            self.confirmation_window.rowconfigure((0, 1), weight=1)
            self.confirmation_window.columnconfigure((0, 1), weight=1)
            self.confirmation_window.minsize(300, 230)
            self.confirmation_window.maxsize(300, 230)
            self.confirmation_window.configure(fg_color=self.colour_root)

            if system() == 'Windows':
                self.confirmation_window.after(200, lambda: self.confirmation_window.iconbitmap(
                    ospath.join(curr_path, "assets/icons/main_icon.ico")))
            elif system() == 'Darwin':
                self.confirmation_window.after(200, lambda: self.confirmation_window.iconbitmap(
                    ospath.join("/", "Applications/LockByte.app")))
                self.confirmation_window.resizable(width=False, height=False)
            else:
                self.confirmation_window.after(
                    200, lambda: self.confirmation_window.iconphoto(True, icon_photo))
                self.confirmation_window.resizable(width=False, height=False)

            # configure password help box
            self.passw_help = ctk.CTkTextbox(
                self.confirmation_window,
                height=80,
                width=300,
                activate_scrollbars=False,
                font=(self.font_text_logs, 12),
                wrap='word',
                fg_color=self.colour4
            )
            self.passw_help.grid(row=0, column=0, columnspan=2,
                                 sticky=ctk.N, padx=10, pady=(10, 40))
            self.passw_help.insert(
                ctk.END, "NOTE: Please remember the password you entered. Your file(s) will become permanently unrecoverable without it.")
            self.passw_help.configure(state="disabled")

            # configure label for password entry
            self.confirm_passw_label = ctk.CTkLabel(
                self.confirmation_window,
                height=25,
                text="Confirm Password :",
                font=(self.font_text_normal, 13)
            )
            self.confirm_passw_label.grid(row=0, rowspan=2, column=0, columnspan=2,
                                          sticky=ctk.NW, padx=10, pady=(105, 0))

            # configure input-box for password entry
            self.confirm_user_passw = ctk.StringVar()
            self.confirm_passw_text = ctk.CTkEntry(
                self.confirmation_window,
                width=156,
                show="\u2022",
                textvariable=self.confirm_user_passw,
                font=(self.font_text_normal, 15)
            )
            self.confirm_passw_text.grid(row=0, rowspan=2, column=0, columnspan=2,
                                         sticky=ctk.NE, padx=10, pady=(105, 0))
            self.confirm_passw_text.bind("<Any-KeyPress>", lambda event,
                                         flg=3: self.delayed_action_call(event, flg))

            # configure switch for keeping/removing original files
            self.keep_files_switch_val = ctk.StringVar()
            self.keep_files_switch = ctk.CTkSwitch(
                self.confirmation_window,
                progress_color=self.colour1,
                variable=self.keep_files_switch_val,
                button_color=("#D5D9DE"),
                onvalue="on",
                offvalue="off",
                font=(self.font_text_normal, 13),
                text="Keep Original Files",
                command=self.keep_file_toogle
            )
            self.keep_files_switch.grid(row=1, column=0, columnspan=2,
                                        sticky=ctk.N, pady=(0, 40))
            self.keep_files_switch.toggle()

            # configure confirm button
            self.confirm_button = ctk.CTkButton(
                self.confirmation_window,
                fg_color=self.colour1,
                width=70,
                text="Confirm",
                font=(self.font_button, 11),
                state="disabled",
                text_color=("black", "white"),
                command=self.on_click_confirm
            )
            self.confirm_button.grid(
                row=1, column=0, sticky=ctk.SE, padx=20, pady=15)

            # configure cancel button
            self.window_cancel_button = ctk.CTkButton(
                self.confirmation_window,
                fg_color=self.colour1,
                width=70,
                text="Cancel",
                font=(self.font_button, 11),
                text_color=("black", "white"),
                command=self.confirmation_window.destroy
            )
            self.window_cancel_button.grid(
                row=1, column=1, sticky=ctk.SW, padx=20, pady=15)

            self.confirmation_window.grab_set()

    # function to toggle switch text
    def keep_file_toogle(self):
        if self.keep_files_switch_val.get() == "off":
            self.keep_files_switch.configure(text="Delete Original Files")
        else:
            self.keep_files_switch.configure(text="Keep Original Files")

    # check if entered confirmation password is of required length
    def check_confirm_pass(self):
        '''
        Function to check if confirmation password meets necessary criteria
        '''
        if len(self.confirm_user_passw.get().strip()) >= 6:
            self.confirm_passw_text.configure(border_color=self.colour1)
            self.confirm_button.configure(state="normal")
        else:
            self.confirm_passw_text.configure(border_color=self.colour2)
            self.confirm_button.configure(state="disabled")
            self.passw_text.configure(border_color=self.colour2)

    # function to verify re-entered password and schedule task
    def on_click_confirm(self):
        '''
        Function to verify re-entered password and schedule task
        '''
        if self.user_passw.get().strip() != self.confirm_user_passw.get().strip():
            self.confirm_passw_text.configure(
                border_color=("#F62A43", "#EF1214"))
            self.passw_help.configure(state="normal")
            self.passw_help.delete("1.0", ctk.END)
            self.passw_help.insert(ctk.END, "Passwords do not match!")
            self.passw_help.configure(state="disabled")
        else:
            self.confirmation_window.destroy()
            if len(self.source_file_location.get().strip()) > 0:
                self.start_thread_pool("file")
            else:
                self.start_thread_pool("folder")

# function to create drag & drop dialog
def create_drag_drop_window(arg_val: str, macOS_instance: App = None) -> ctk.CTkToplevel:
    '''
    Function to create new window dialog for user to choose action to perform on dropped folder

    :param arg_val: file/folder path to be handled
    :param macOS_instance: if current os is MacOS, handle app_instance accordingly
    '''
    arguments = {
        'class': "LockByte",
        'master': app_root
    }
    drag_drop_window = ctk.CTkToplevel(**arguments)
    drag_drop_window.title("Choose An Option")
    x = app_root.winfo_x()
    y = app_root.winfo_y()
    drag_drop_window.geometry(
        "%dx%d+%d+%d" % (400, 100, x + 1, y + 1))
    drag_drop_window.resizable(width=False, height=False)
    drag_drop_window.rowconfigure((0, 1), weight=1)
    drag_drop_window.columnconfigure((0, 1), weight=1)

    if system() == 'Windows':
        drag_drop_window.after(200, lambda: drag_drop_window.iconbitmap(ospath.join(ospath.dirname(ospath.realpath(__file__)),
                                                                                    "assets/icons/main_icon.ico")))
    elif system() == 'Darwin':
        drag_drop_window.after(200, lambda: drag_drop_window.iconbitmap(
            ospath.join("/", "Applications/LockByte.app")))
    else:
        drag_drop_window.after(
            200, lambda: drag_drop_window.iconphoto(True, icon_photo))

    message_text_box = ctk.CTkTextbox(
        drag_drop_window,
        fg_color=drag_drop_window._fg_color,
        height=30,
        width=310,
        wrap='word',
        activate_scrollbars=False,
        font=("Aileron", 15),
    )
    message_text_box.grid(column=0, columnspan=2, row=0,
                          sticky=ctk.NS, pady=(10, 5))
    message_text_box.insert(
        ctk.END, "What would you like to do with this folder ?")
    message_text_box.configure(state="disabled")

    # configure option buttons
    button_encrypt = ctk.CTkButton(
        drag_drop_window,
        fg_color=("#36c3eb", "#0078F0"),
        text_color=("black", "white"),
        height=28,
        width=50,
        font=("Aileron Bold", 11),
        image=ctk.CTkImage(light_image=Image.open(ospath.join(curr_path,
                                                              "assets/icons/lock-light-mode.png")),
                           dark_image=Image.open(ospath.join(curr_path,
                                                             "assets/icons/lock-dark-mode.png")),
                           size=(12, 12)),
        compound="right",
        anchor="w",
        text="Encrypt",
        command=lambda: on_click_action_button(arg_val, 1, macOS_instance)
    )
    button_encrypt.grid(column=0, row=1, sticky=ctk.SE, padx=20, pady=(0, 12))

    button_decrypt = ctk.CTkButton(
        drag_drop_window,
        fg_color=("#36c3eb", "#0078F0"),
        text_color=("black", "white"),
        height=28,
        width=50,
        font=("Aileron Bold", 11),
        image=ctk.CTkImage(light_image=Image.open(ospath.join(curr_path,
                                                              "assets/icons/unlock-light-mode.png")),
                           dark_image=Image.open(ospath.join(curr_path,
                                                             "assets/icons/unlock-dark-mode.png")),
                           size=(12, 12)),
        compound="right",
        anchor="w",
        text="Decrypt",
        command=lambda: on_click_action_button(arg_val, 0, macOS_instance)
    )
    button_decrypt.grid(column=1, row=1, sticky=ctk.SW, padx=20, pady=(0, 12))
    drag_drop_window.protocol(
        "WM_DELETE_WINDOW", drag_drop_window.master.destroy)
    return drag_drop_window

# function to switch to main app window from drag & drop dialog
def on_click_action_button(arg_val: str, mode: int, macOS_instance: App):
    '''
    Function to switch to main app window from drag & drop dialog based on user choice

    :param arg_val: file/folder path to be handled
    :param mode: mode (Encryption/Decryption) selected by the user
    :param macOS_instance: if current os is MacOS, handle app_instance accordingly
    '''
    drag_drop_win.destroy()
    if macOS_instance is None:
        app_instance = App(app_root)
    else:
        app_instance = macOS_instance
    if app_instance.index == 0:  # user is currently on home page
        if mode == 0:
            app_instance.change_window(mode=0)
        else:
            app_instance.change_window(mode=1, new=" New ", width=225)
    else:  # user is currently on action page
        app_instance.on_click_back(1)
        if mode == 0:
            app_instance.passw_label.configure(text="Enter Password :")
            app_instance.passw_text.configure(width=251)
            app_instance.action_button.configure(text="Decrypt")
        else:
            app_instance.passw_label.configure(text="Enter New Password :")
            app_instance.passw_text.configure(width=221)
            app_instance.action_button.configure(text="Encrypt")

    app_instance.source_folder_text.insert(0, arg_val)
    app_instance.disable_file_pick()
    app_root.deiconify()
    app_instance.master.protocol(
        "WM_DELETE_WINDOW", app_root.destroy)

# function to handle multiple instances of the app
def on_detect_second_instance(root_to_kill: ctk.CTk = None):
    '''
    Function to prevent user from simultaneously running multiple instances 

    :param root_to_kill: customtkinter instance to kill on exit
    '''
    arguments = {
        'class': "LockByte",
        'master': app_root
    }
    warning_window = ctk.CTkToplevel(**arguments)
    warning_window.title("Instance Already Running")
    warning_window.geometry("450x100")
    warning_window.resizable(width=False, height=False)
    warning_window.rowconfigure((0, 1), weight=1)
    warning_window.columnconfigure(0, weight=1)
    if root_to_kill == None:
        root_to_kill = warning_window

    if system() == 'Windows':
        warning_window.after(200, lambda: warning_window.iconbitmap(ospath.join(ospath.dirname(ospath.realpath(__file__)),
                                                                                "assets/icons/main_icon.ico")))
    elif system() == 'Darwin':
        warning_window.after(200, lambda: warning_window.iconbitmap(
            ospath.join("/", "Applications/LockByte.app")))
    else:
        warning_window.after(
            200, lambda: warning_window.iconphoto(True, icon_photo))

    message_text_box = ctk.CTkTextbox(
        warning_window,
        fg_color=warning_window._fg_color,
        height=30,
        width=310,
        wrap='word',
        activate_scrollbars=False,
        font=("Aileron", 15),
    )
    message_text_box.grid(column=0, rowspan=2, row=0, padx=10,
                          sticky=ctk.NSEW)
    message_text_box.insert(
        ctk.END, "Another instance of LockByte is already running. Please close any open instances and try again.")
    message_text_box.configure(state="disabled")

    # configure dismiss button
    button_dismiss = ctk.CTkButton(
        warning_window,
        fg_color=("#36c3eb", "#0078F0"),
        text_color=("black", "white"),
        height=28,
        width=50,
        font=("Aileron Bold", 11),
        text="OK",
        anchor="center",
        command=lambda: root_to_kill.destroy()
    )
    button_dismiss.grid(column=0, row=1, sticky=ctk.S, pady=(0, 12))
    warning_window.protocol(
        "WM_DELETE_WINDOW", root_to_kill.destroy)

# function to manage files dropped onto the application (MacOS-only)
def handle_sys_args(*args, app_instance: App):
    '''
    Function to support MacOS specific functionality of dragging and dropping files onto the dock

    :param app_instance: current app_instance
    '''
    global drag_drop_win
    if len(jobs) < 1:
        if ospath.isdir(args[0]):
            app_root.iconify()
            drag_drop_win = create_drag_drop_window(args[0], app_instance)

        else:
            if args[0].split('.')[-1] == 'lockbyte':
                if app_instance.index == 0:  # user is currently on home page
                    app_instance.change_window(mode=0)
                else:  # user is currently on action page
                    app_instance.on_click_back(1)
                    app_instance.passw_label.configure(text="Enter Password :")
                    app_instance.passw_text.configure(width=251)
                    app_instance.action_button.configure(text="Decrypt")
            else:
                if app_instance.index == 0:  # user is currently on home page
                    app_instance.change_window(mode=1, new=" New ", width=221)
                else:  # user is currently on action page
                    app_instance.on_click_back(1)
                    app_instance.passw_label.configure(
                        text="Enter New Password :")
                    app_instance.passw_text.configure(width=221)
                    app_instance.action_button.configure(text="Encrypt")

            app_instance.source_file_text.insert(0, args[0])
            app_instance.disable_folder_pick()
    else:
        on_detect_second_instance()

# main caller function
def main():
    '''
    Main caller function
    '''
    global curr_path, app_root, fh, drag_drop_win
    curr_path = ospath.dirname(ospath.realpath(__file__))
    print(curr_path)

    # load fonts
    ctk.FontManager.load_font(ospath.join(
        curr_path, "assets/fonts/WorkSans/WorkSans-ExtraLight.ttf"))
    ctk.FontManager.load_font(ospath.join(
        curr_path, "assets/fonts/Aileron/Aileron-Regular.ttf"))
    ctk.FontManager.load_font(ospath.join(
        curr_path, "assets/fonts/Aileron/Aileron-Bold.ttf"))
    ctk.FontManager.load_font(ospath.join(
        curr_path, "assets/fonts/OfficeCodePro/OfficeCodePro-Regular.ttf"))

    # flag variables
    multi_instance_flag = False

    app_root = ctk.CTk(className="LockByte")
    app_root.title("LockByte")
    app_root.geometry("400x500")
    app_root.minsize(400, 500)
    app_root.maxsize(400, 500)
    app_root.resizable(width=False, height=False)

    if system() == 'Windows':
        app_root.iconbitmap(ospath.join(
            curr_path, "assets/icons/main_icon.ico"))
    elif system() == 'Darwin':
        global icon_photo
        app_root.iconbitmap(ospath.join("/", "Applications/LockByte.app"))
        app_root.createcommand(
            'tk::mac::OpenDocument', lambda *args: handle_sys_args(*args, app_instance=app_instance))
    else:
        global icon_photo
        icon_photo = ImageTk.PhotoImage(file=ospath.join(
            curr_path, "assets/icons/main_icon.png"))
        app_root.after(200, lambda: app_root.call(
            'wm', 'iconphoto', app_root._w, icon_photo))

    # multi-instance blocking
    if system() == 'Windows':
        import win32event
        import win32api
        import winerror
        app_identifier = 'LockByte_bosekb_180601'
        mutex = win32event.CreateMutex(None, False, app_identifier)
        if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
            multi_instance_flag = True
            app_root.withdraw()
            on_detect_second_instance(app_root)
    else:
        import fcntl
        fh = None
        LOCK_PATH = ospath.join(curr_path, "lock")
        try:
            fh = open(LOCK_PATH, 'w')
            fcntl.lockf(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except EnvironmentError as err:
            if fh is not None:
                multi_instance_flag = True
                app_root.withdraw()
                on_detect_second_instance(app_root)
                fh = None
            else:
                pass

    # manage files dropped onto the application (Windows & Linux)
    if not system() == 'Darwin' and len(argv) > 1 and not multi_instance_flag:
        if ospath.isdir(argv[1]):
            app_root.withdraw()
            drag_drop_win = create_drag_drop_window(argv[1])
        else:
            if argv[1].split('.')[-1] == 'lockbyte':
                app_instance = App(app_root)
                app_instance.change_window(mode=0)
            else:
                app_instance = App(app_root)
                app_instance.change_window(mode=1, new=" New ", width=221)

            app_instance.source_file_text.insert(0, argv[1])
            app_instance.disable_folder_pick()
    elif not multi_instance_flag:
        app_instance = App(app_root)

    # create menu items (MacOS-only)
    if system() == 'Darwin':
        menubar = Menu(app_root)
        appmenu = Menu(menubar, name='apple')
        menubar.add_cascade(menu=appmenu)
        appmenu.add_command(label='About LockByte',
                            command=app_instance.create_info_window)
        appmenu.add_separator()
        app_root.config(menu=menubar)

    app_root.mainloop()

    if system() == 'Windows':
        win32api.CloseHandle(mutex)
    else:
        try:
            if fh is not None:
                fcntl.lockf(fh, fcntl.LOCK_UN)
                fh.close()
                unlink(LOCK_PATH)
        except Exception as err:
            pass


if __name__ == "__main__":
    main()
