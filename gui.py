# gui.py

from config import SYSTEM_PROMPT_PAIRS, AI_MODELS

import os
from datetime import datetime
from PIL import Image, ImageEnhance, ImageTk
import tkinter as tk
from tkinter import scrolledtext, ttk, filedialog
import requests
from io import BytesIO
import threading
import shutil

class AIGUI:
    def __init__(self, master):
        self.master = master
        self.conversation = []
        self.turn_count = 0
        self.images = []
        self.image_paths = []
        master.title("Neural Link Interface v1.0")
        
        # Configure window for full screen and resizing
        master.geometry("1200x800")  # Default size
        master.minsize(800, 600)     # Minimum size
        
        # Configure grid weights for proper resizing
        master.grid_rowconfigure(0, weight=1)
        master.grid_columnconfigure(0, weight=1)
        
        # Cyberpunk color scheme
        self.colors = {
            'bg': '#0a0a0f',           # Deep space black
            'text_bg': '#0f1117',      # Dark background for text
            'text_fg': '#00ff9f',      # Neon green text
            'input_bg': '#1a1a24',     # Dark input background
            'input_fg': '#00ffff',     # Cyan input text
            'accent': '#ff0066',       # Neon pink accent
            'accent_hover': '#ff1a75', # Lighter neon pink
            'button_bg': '#1a1a24',    # Dark button background
            'border': '#00ffff',       # Cyan border
            'highlight': '#ff0066',    # Neon pink highlight
            'label_fg': '#00ccff',     # Bright blue for labels
            'status_fg': '#ff9900'     # Orange for status
        }
        
        # Configure window style
        master.configure(bg=self.colors['bg'])
        
        # Style configuration
        style = ttk.Style()
        style.configure('Cyberpunk.TFrame', background=self.colors['bg'])
        style.configure('Cyberpunk.TCombobox',
            fieldbackground=self.colors['input_bg'],
            background=self.colors['input_bg'],
            foreground=self.colors['input_fg'],
            arrowcolor=self.colors['accent'],
            selectbackground=self.colors['accent']
        )
        
        # Main container frame with proper weights
        self.main_frame = ttk.Frame(master, padding="20", style='Cyberpunk.TFrame')
        self.main_frame.grid(row=0, column=0, sticky='nsew')
        self.main_frame.grid_rowconfigure(0, weight=1)  # Make text area expand
        self.main_frame.grid_columnconfigure(0, weight=1)  # Make columns expand
        
        # Text area with cyberpunk styling and proper expansion
        text_frame = tk.Frame(
            self.main_frame,
            bg=self.colors['border'],
            bd=1,
            relief='solid'
        )
        text_frame.grid(row=0, column=0, sticky='nsew', pady=(0, 15))
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)
        
        self.text_area = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.WORD,
            bg=self.colors['text_bg'],
            fg=self.colors['text_fg'],
            insertbackground=self.colors['accent'],
            font=('Consolas', 10),
            padx=15,
            pady=15,
            relief='flat',
            borderwidth=0,
            selectbackground=self.colors['accent'],
            selectforeground='white'
        )
        self.text_area.grid(row=0, column=0, sticky='nsew', padx=1, pady=1)
        
        # Input field with neon glow effect
        input_frame = tk.Frame(
            self.main_frame,
            bg=self.colors['border'],
            relief='solid',
            bd=1
        )
        input_frame.grid(row=2, column=0, sticky='ew')
        
        self.input_field = tk.Entry(
            input_frame,
            bg=self.colors['input_bg'],
            fg=self.colors['input_fg'],
            insertbackground=self.colors['accent'],
            font=('Consolas', 11),
            relief='flat',
            bd=0
        )
        self.input_field.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=10)
        
        # Submit button with neon effect
        self.submit_button = tk.Button(
            input_frame,
            text="TRANSMIT",
            command=self.submit_input,
            bg=self.colors['accent'],
            fg='white',
            activebackground=self.colors['accent_hover'],
            activeforeground='white',
            relief='flat',
            bd=0,
            padx=20,
            pady=8,
            font=('Orbitron', 10),
            cursor='hand2'
        )
        self.submit_button.pack(side=tk.RIGHT, padx=10, pady=10)
        
        # Status bar with cyberpunk styling
        self.status_bar = tk.Label(
            self.main_frame,
            text=">> SYSTEM READY <<",
            bg=self.colors['bg'],
            fg=self.colors['status_fg'],
            bd=1,
            relief=tk.SUNKEN,
            anchor=tk.W,
            padx=10,
            font=('Share Tech Mono', 9)
        )
        self.status_bar.grid(row=3, column=0, sticky='ew')
        
        # Loading animation characters (more cyberpunk)
        self.loading_chars = ["◢", "◣", "◤", "◥"]
        
        # Control panel frame
        control_frame = tk.Frame(
            self.main_frame,
            bg=self.colors['bg'],
            relief='flat'
        )
        control_frame.grid(row=1, column=0, sticky='ew', pady=(0, 15))
        
        # Mode selection
        mode_frame = tk.Frame(control_frame, bg=self.colors['bg'])
        mode_frame.pack(side=tk.LEFT, padx=5)
        
        tk.Label(
            mode_frame,
            text="Mode:",
            bg=self.colors['bg'],
            fg=self.colors['label_fg'],
            font=('Segoe UI', 10)
        ).pack(side=tk.LEFT, padx=5)
        
        self.mode_var = tk.StringVar(value="AI-AI")
        mode_dropdown = ttk.Combobox(
            mode_frame,
            textvariable=self.mode_var,
            values=["AI-AI", "Human-AI"],
            width=10,
            state="readonly"
        )
        mode_dropdown.pack(side=tk.LEFT, padx=5)
        
        # Turns selection with modern styling
        turns_frame = tk.Frame(control_frame, bg=self.colors['bg'])
        turns_frame.pack(side=tk.LEFT, padx=5)
        
        tk.Label(
            turns_frame,
            text="Iterations:",
            bg=self.colors['bg'],
            fg=self.colors['label_fg'],
            font=('Segoe UI', 10)
        ).pack(side=tk.LEFT, padx=5)
        
        self.turns_var = tk.StringVar(value="4")
        self.turns_dropdown = ttk.Combobox(
            turns_frame,
            textvariable=self.turns_var,
            values=["2", "4", "6", "8", "10"],
            width=5,
            state="readonly"
        )
        self.turns_dropdown.pack(side=tk.LEFT, padx=5)

        # Model selections
        for i, (label, var_name) in enumerate([
            ("AI-1 Model:", "ai_1_model_var"),
            ("AI-2 Model:", "ai_2_model_var")
        ]):
            model_frame = tk.Frame(control_frame, bg=self.colors['bg'])
            model_frame.pack(side=tk.LEFT, padx=20)
            
            tk.Label(
                model_frame,
                text=label,
                bg=self.colors['bg'],
                fg=self.colors['label_fg'],
                font=('Segoe UI', 10)
            ).pack(side=tk.LEFT, padx=5)
            
            setattr(self, var_name, tk.StringVar(value=list(AI_MODELS.keys())[i]))
            ttk.Combobox(
                model_frame,
                textvariable=getattr(self, var_name),
                values=list(AI_MODELS.keys()),
                width=15,
                state="readonly"
            ).pack(side=tk.LEFT, padx=5)

        # Prompt pair selection
        prompt_frame = tk.Frame(control_frame, bg=self.colors['bg'])
        prompt_frame.pack(side=tk.LEFT, padx=20)
        
        tk.Label(
            prompt_frame,
            text="Prompt Style:",
            bg=self.colors['bg'],
            fg=self.colors['label_fg'],
            font=('Segoe UI', 10)
        ).pack(side=tk.LEFT, padx=5)
        
        self.prompt_pair_var = tk.StringVar(value=list(SYSTEM_PROMPT_PAIRS.keys())[0])
        self.prompt_pair_dropdown = ttk.Combobox(
            prompt_frame,
            textvariable=self.prompt_pair_var,
            values=list(SYSTEM_PROMPT_PAIRS.keys()),
            width=20,
            state="readonly"
        )
        self.prompt_pair_dropdown.pack(side=tk.LEFT, padx=5)

        # Export button
        self.export_button = tk.Button(
            control_frame,
            text="Export",
            command=self.export_conversation,
            bg=self.colors['button_bg'],
            fg=self.colors['label_fg'],
            activebackground=self.colors['accent'],
            activeforeground='white',
            relief='flat',
            bd=0,
            padx=15,
            pady=6,
            font=('Segoe UI', 10),
            cursor='hand2'
        )
        self.export_button.pack(side=tk.RIGHT, padx=5)

        # Bind events
        self.input_field.bind('<Return>', lambda e: self.submit_input())
        self.input_callback = None

        # Add hover effects
        for button in [self.submit_button, self.export_button]:
            button.bind('<Enter>', self._on_button_hover)
            button.bind('<Leave>', self._on_button_leave)

        # Add loading indicator
        self.loading = False
        self.loading_index = 0

        # Bind keyboard shortcuts
        self.master.bind('<Control-Return>', lambda e: self.submit_input())  # Ctrl+Enter to submit
        self.master.bind('<Control-l>', lambda e: self.clear_conversation())  # Ctrl+L to clear
        self.master.bind('<Control-s>', lambda e: self.export_conversation())  # Ctrl+S to save
        
        # Add tooltips
        self.create_tooltip(self.submit_button, "Send message (Enter)")
        self.create_tooltip(self.export_button, "Export conversation (Ctrl+S)")
        self.create_tooltip(mode_dropdown, "Switch between AI-AI chat and Human-AI chat")
        self.create_tooltip(self.turns_dropdown, "Number of conversation turns")

        # Add maximize button functionality
        self.master.bind('<F11>', self.toggle_fullscreen)
        self.master.bind('<Escape>', self.end_fullscreen)
        self.fullscreen = False

    def _on_button_hover(self, event):
        if event.widget == self.submit_button:
            event.widget.configure(bg=self.colors['accent_hover'])
        else:
            event.widget.configure(bg=self.colors['accent'])

    def _on_button_leave(self, event):
        if event.widget == self.submit_button:
            event.widget.configure(bg=self.colors['accent'])
        else:
            event.widget.configure(bg=self.colors['button_bg'])

    def export_conversation(self):
        """Export conversation and save any images"""
        try:
            # Create timestamp for unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create export directory if it doesn't exist
            export_dir = "exports"
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
            
            # Create conversation directory
            conversation_dir = os.path.join(export_dir, f"conversation_{timestamp}")
            os.makedirs(conversation_dir)
            
            # Export text
            text_path = os.path.join(conversation_dir, "conversation.txt")
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(self.text_area.get('1.0', tk.END))
            
            # Copy images if any
            if self.image_paths:
                images_dir = os.path.join(conversation_dir, "images")
                os.makedirs(images_dir)
                for i, image_path in enumerate(self.image_paths):
                    if os.path.exists(image_path):
                        ext = os.path.splitext(image_path)[1]
                        new_path = os.path.join(images_dir, f"image_{i}{ext}")
                        shutil.copy2(image_path, new_path)
            
            self.append_text(f"\nConversation exported to: {conversation_dir}\n")
            
        except Exception as e:
            print(f"Error exporting conversation: {e}")
            self.append_text(f"\nError exporting conversation: {e}\n")

    def display_image(self, image_url):
        """Display an image from URL in the text area"""
        try:
            # Check if the URL is actually a local path (starts with 'generated_')
            if image_url.startswith(('generated_', 'images/generated_')):
                local_path = image_url  # Use existing path
            else:
                # Create images directory if it doesn't exist
                if not os.path.exists('images'):
                    os.makedirs('images')
                    
                # Generate a filename from timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                local_path = os.path.join('images', f'generated_{timestamp}.jpg')
                
                # Download the image
                response = requests.get(image_url)
                response.raise_for_status()
                
                # Save the image locally
                with open(local_path, 'wb') as f:
                    f.write(response.content)
            
            # Open and resize image
            image = Image.open(local_path)
            # Calculate new size while maintaining aspect ratio
            max_width = 400
            ratio = max_width / image.width
            new_size = (int(image.width * ratio), int(image.height * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage and store reference
            photo = ImageTk.PhotoImage(image)
            self.images.append(photo)
            
            # Insert image into text area
            self.text_area.insert('end', '\n')
            self.text_area.image_create('end-1c', image=photo)
            self.text_area.insert('end', '\n\n')
            
            # Store image path only if it's not already stored
            if local_path not in self.image_paths:
                self.image_paths.append(local_path)
            
        except Exception as e:
            print(f"Error loading image: {e}")
            self.append_text(f"\nError loading image: {e}\n")

    def append_text(self, text):
        """Append text to the text area without auto-scrolling"""
        self.text_area.insert('end', text)

    def update_loading(self):
        if self.loading:
            self.loading_index = (self.loading_index + 1) % len(self.loading_chars)
            self.status_bar.config(
                text=f">> {self.loading_chars[self.loading_index]} PROCESSING NEURAL LINK {self.loading_chars[(self.loading_index + 2) % 4]} <<",
                fg=self.colors['accent']
            )
            self.master.after(100, self.update_loading)
            
    def start_loading(self):
        self.loading = True
        self.update_loading()
        self.input_field.config(state='disabled')
        self.submit_button.config(state='disabled')
        
    def stop_loading(self):
        self.loading = False
        self.status_bar.config(text=">> SYSTEM READY <<", fg=self.colors['status_fg'])
        self.input_field.config(state='normal')
        self.submit_button.config(state='normal')
        self.input_field.focus_set()
        
    def submit_input(self):
        if self.input_callback and not self.loading:
            self.start_loading()
            self.input_callback()  # No need to pass input, it will get it from the field

    def set_input_callback(self, callback):
        self.input_callback = callback

    def create_tooltip(self, widget, text):
        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            
            label = tk.Label(
                tooltip,
                text=text,
                bg=self.colors['bg'],
                fg=self.colors['label_fg'],
                relief='solid',
                borderwidth=1,
                font=('Segoe UI', 9)
            )
            label.pack()
            
            def hide_tooltip():
                tooltip.destroy()
            
            widget.tooltip = tooltip
            widget.bind('<Leave>', lambda e: hide_tooltip())
            
        widget.bind('<Enter>', show_tooltip)
        
    def clear_conversation(self):
        """Clear the conversation history"""
        if not self.loading:
            self.text_area.delete('1.0', tk.END)
            self.conversation = []
            self.turn_count = 0
            self.images = []
            self.image_paths = []
            self.status_bar.config(text=">> NEURAL LINK RESET <<", fg=self.colors['status_fg'])
            self.append_text("[ Neural interface initialized. Ready for new input. ]\n")

    def toggle_fullscreen(self, event=None):
        self.fullscreen = not self.fullscreen
        self.master.attributes('-fullscreen', self.fullscreen)
        
    def end_fullscreen(self, event=None):
        self.fullscreen = False
        self.master.attributes('-fullscreen', False)

def create_gui():
    root = tk.Tk()
    return AIGUI(root)

def run_gui(gui):
    gui.master.mainloop()