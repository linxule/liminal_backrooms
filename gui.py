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
            'status_fg': '#ff9900',    # Orange for status
            'selected_bg': '#2a2a44'   # Dark purple for text selection
        }
        
        # Add branch tracking
        self.branch_conversations = {}  # Store branch conversations by selection_index
        self.active_branch = None      # Currently displayed branch
        self.branch_tree = {}          # Tree structure of branches
        master.title("LiminalBackrooms v1.0")
        
        # Configure window for full screen and resizing
        master.geometry("1600x900")  # Larger default size for split view
        master.minsize(1200, 800)    # Larger minimum size
        
        # Configure grid weights for proper resizing
        master.grid_rowconfigure(0, weight=1)
        master.grid_columnconfigure(0, weight=3)  # Main content area
        master.grid_columnconfigure(1, weight=1)  # Branch tree area
        
        # Create left and right panes
        self.left_pane = ttk.Frame(master, padding="10", style='Cyberpunk.TFrame')
        self.left_pane.grid(row=0, column=0, sticky='nsew')
        
        self.right_pane = ttk.Frame(master, padding="10", style='Cyberpunk.TFrame')
        self.right_pane.grid(row=0, column=1, sticky='nsew')
        
        # Configure pane weights
        self.left_pane.grid_rowconfigure(0, weight=1)
        self.left_pane.grid_columnconfigure(0, weight=1)
        self.right_pane.grid_rowconfigure(1, weight=1)  # Row 0 for title, 1 for tree
        self.right_pane.grid_columnconfigure(0, weight=1)
        
        # Add title to right pane
        self.branch_title = tk.Label(
            self.right_pane,
            text="Conversation Branches",
            bg=self.colors['bg'],
            fg=self.colors['label_fg'],
            font=('Orbitron', 12)
        )
        self.branch_title.grid(row=0, column=0, pady=(0, 10), sticky='ew')
        
        # Create tree view for branches
        self.branch_tree_view = ttk.Treeview(
            self.right_pane,
            style='Cyberpunk.Treeview',
            selectmode='browse'
        )
        self.branch_tree_view.grid(row=1, column=0, sticky='nsew')
        
        # Configure tree view style
        style = ttk.Style()
        style.configure('Cyberpunk.Treeview',
            background=self.colors['text_bg'],
            foreground=self.colors['text_fg'],
            fieldbackground=self.colors['text_bg'],
            borderwidth=1,
            relief='solid'
        )
        style.configure('Cyberpunk.Treeview.Heading',
            background=self.colors['bg'],
            foreground=self.colors['label_fg'],
            borderwidth=1,
            relief='solid'
        )
        
        # Configure tree view with additional columns
        self.branch_tree_view["columns"] = ("concept", "depth")
        self.branch_tree_view.column("#0", width=30, stretch=tk.NO)  # Icon column
        self.branch_tree_view.column("concept", width=250, anchor=tk.W)
        self.branch_tree_view.column("depth", width=50, anchor=tk.CENTER)
        
        self.branch_tree_view.heading("#0", text="")
        self.branch_tree_view.heading("concept", text="Branch Concepts")
        self.branch_tree_view.heading("depth", text="Depth")
        
        # Initialize main conversation as root node with visual indicator
        self.branch_tree_view.insert('', 'end', 'main', text='⚡', values=('Main Conversation', '0'))
        
        # Add visual tags for different branch levels
        self.branch_tree_view.tag_configure('main', foreground=self.colors['accent'])
        self.branch_tree_view.tag_configure('branch', foreground=self.colors['text_fg'])
        self.branch_tree_view.tag_configure('active', background=self.colors['selected_bg'])
        
        # Add scrollbar for tree
        tree_scroll = ttk.Scrollbar(
            self.right_pane,
            orient="vertical",
            command=self.branch_tree_view.yview
        )
        tree_scroll.grid(row=1, column=1, sticky='ns')
        self.branch_tree_view.configure(yscrollcommand=tree_scroll.set)
        
        # Bind tree selection event
        self.branch_tree_view.bind('<<TreeviewSelect>>', self.on_branch_select)
        
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
            selectbackground=self.colors['selected_bg'],
            selectforeground=self.colors['text_fg']
        )
        self.text_area.grid(row=0, column=0, sticky='nsew', padx=1, pady=1)
        
        # Create right-click context menu
        self.context_menu = tk.Menu(self.master, tearoff=0, bg=self.colors['bg'], fg=self.colors['text_fg'])
        self.context_menu.add_command(
            label="🕳️ Rabbithole Selection",
            command=self.branch_from_selection
        )
        self.context_menu.add_command(
            label="🧶 Loom Forward",
            command=self.loom_from_selection
        )
        
        # Bind right-click event
        self.text_area.bind('<Button-3>', self.show_context_menu)
        
        # Bind selection events
        self.text_area.bind('<<Selection>>', self.on_selection)
        
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
        
        self.turns_var = tk.StringVar(value="1")
        self.turns_dropdown = ttk.Combobox(
            turns_frame,
            textvariable=self.turns_var,
            values=["1", "2", "4", "6", "8", "100"],
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
            
            # Set both dropdowns to the first model in the config
            setattr(self, var_name, tk.StringVar(value=list(AI_MODELS.keys())[0]))
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
            text="Scenario:",
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
                text=f">> {self.loading_chars[self.loading_index]} SPROUTING {self.loading_chars[(self.loading_index + 2) % 4]} <<",
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
        """Handle input submission for both main conversation and branches"""
        if self.input_callback and not self.loading:
            input_text = self.input_field.get().strip()
            self.input_field.delete(0, tk.END)
            
            # Get the current conversation based on active branch
            if self.active_branch:
                current_conversation = self.branch_conversations[self.active_branch]
                
                # Add the input to the branch conversation if there is any
                if input_text:
                    current_conversation['conversation'].append({
                        "role": "user",
                        "content": input_text
                    })
                    self.display_conversation(current_conversation['conversation'], self.text_area)
                
                # Start processing
                self.start_loading()
                self.process_branch_conversation(self.active_branch)
            else:
                # Handle main conversation
                self.start_loading()
                self.input_callback()

    def _append_to_branch(self, text, branch_id):
        """Internal method to append text to a branch conversation"""
        if self.active_branch == branch_id:  # Only update if we're still viewing this branch
            self.text_area.insert('end', text)
            self.text_area.see('end')

    def process_branch_conversation(self, branch_id):
        """Process the branch conversation using the selected models"""
        try:
            branch_data = self.branch_conversations[branch_id]
            
            # Get current max turns from dropdown
            max_turns = int(self.turns_var.get())
            
            # Check if we've reached max turns for this branch
            if branch_data['turn_count'] >= max_turns:
                # Don't reset turn count, just start a new set
                branch_data['turn_count'] = 0
                # Update the history to include all conversation up to this point
                branch_data['history'] = self.text_area.get('1.0', tk.END)
            
            # Import ai_turn here to avoid circular imports
            from main import ai_turn
            
            # Get the current prompt pair
            prompt_pair = SYSTEM_PROMPT_PAIRS[self.prompt_pair_var.get()]
            
            # Create a special system prompt for the branch that includes the context
            branch_context = branch_data['history']
            
            # Build parent context by traversing up the tree
            parent_context = ""
            current_parent_id = branch_data['parent_id']
            while current_parent_id != 'main':
                parent_branch = self.branch_conversations.get(current_parent_id)
                if parent_branch:
                    parent_text = parent_branch['selected_text']
                    parent_context = f"This is a sub-branch of a conversation about '{parent_text}'. " + parent_context
                    current_parent_id = parent_branch['parent_id']
                else:
                    break
            
            # Create different prompts based on branch type
            if branch_data.get('type') == 'loom':
                branch_prompt = (
                    f"The following is the conversation context up to this point:\n\n{branch_context}\n\n"
                    f"{parent_context}"
                    f"You are now continuing the conversation from exactly this point: '{branch_data['selected_text']}'. "
                    f"Complete this thought or sentence naturally, as if you were the original speaker, "
                    f"maintaining the same tone, style, and flow. Then continue the conversation forward "
                    f"from there. Do not repeat or rephrase the selected text - start immediately with "
                    f"the continuation of that thought."
                )
            else:
                branch_prompt = (
                    f"The following is the conversation context up to this point:\n\n{branch_context}\n\n"
                    f"{parent_context}"
                    f"Now, let's explore and expand upon the concept of '{branch_data['selected_text']}' that emerged in this context. "
                    f"Use the previous context to inform the discussion, but focus on developing and expanding upon "
                    f"this specific concept in depth."
                )
            
            # Get selected models
            ai_1_model = self.ai_1_model_var.get()
            ai_2_model = self.ai_2_model_var.get()
            
            # Combine branch prompt with the regular system prompts
            ai_1_prompt = branch_prompt + "\n\n" + prompt_pair["AI_1"]
            ai_2_prompt = branch_prompt + "\n\n" + prompt_pair["AI_2"]
            
            def append_to_branch(text):
                """Wrapper to append text to the branch conversation"""
                # Use after() to safely update GUI from thread
                self.master.after(0, lambda: self._append_to_branch(text, branch_id))
            
            def process_next_turn():
                """Process the next turn in the conversation"""
                try:
                    # Process AI-1's turn
                    branch_data['conversation'] = ai_turn(
                        "AI-1",
                        branch_data['conversation'],
                        ai_1_model,
                        ai_1_prompt,
                        gui=None,
                        is_branch=True,
                        branch_output=append_to_branch
                    )
                    
                    # Process AI-2's turn
                    branch_data['conversation'] = ai_turn(
                        "AI-2",
                        branch_data['conversation'],
                        ai_2_model,
                        ai_2_prompt,
                        gui=None,
                        is_branch=True,
                        branch_output=append_to_branch
                    )
                    
                    branch_data['turn_count'] += 1
                    
                    # Show remaining turns
                    remaining_turns = max_turns - branch_data['turn_count']
                    if remaining_turns > 0:
                        append_to_branch(f"\n({remaining_turns} turns remaining in this branch)\n")
                        # Schedule the next turn with a delay
                        self.master.after(1000, lambda: self.process_branch_conversation(branch_id))
                    else:
                        # Show different completion message based on branch type
                        if branch_data.get('type') == 'loom':
                            append_to_branch("\n🧶 Loom paused. Click transmit to continue deeper.\n")
                        else:
                            append_to_branch("\n🕳️ Branch exploration paused. Click transmit to continue deeper.\n")
                        self.master.after(0, self.stop_loading)
                        
                except Exception as e:
                    error_msg = f"\nError in branch turn: {str(e)}\n"
                    self.master.after(0, lambda: self._append_to_branch(error_msg, branch_id))
                    self.master.after(0, self.stop_loading)
            
            # Start processing this turn in a new thread
            thread = threading.Thread(target=process_next_turn)
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            error_msg = f"\nError in branch conversation: {str(e)}\n"
            self.master.after(0, lambda: self.text_area.insert('end', error_msg))
            self.master.after(0, lambda: self.text_area.see('end'))
            print(f"Branch conversation error: {e}")
            self.master.after(0, self.stop_loading)

    def display_conversation(self, conversation, text_area):
        """Display the selected conversation in the text area with context"""
        text_area.delete('1.0', tk.END)
        
        # If this is a branch conversation, show the context and path
        if self.active_branch:
            branch_data = self.branch_conversations[self.active_branch]
            path = self.get_branch_path(self.active_branch)
            text_area.insert('end', f"=== Branch Path: {path} ===\n\n")
            text_area.insert('end', "=== Original Conversation Context ===\n\n")
            text_area.insert('end', branch_data['history'])
            
            # Show different header based on branch type
            if branch_data.get('type') == 'loom':
                text_area.insert('end', f"\n\n=== 🧶 Looming forward from: '{branch_data['selected_text']}' ===\n\n")
            else:
                text_area.insert('end', f"\n\n=== 🕳️ Rabbitholing on: '{branch_data['selected_text']}' ===\n\n")
        
        # Display the conversation messages
        for msg in conversation:
            if isinstance(msg, dict):
                if msg["role"] == "user":
                    # Skip the initial branch message since we already showed it in the header
                    if self.active_branch and msg.get('display', '').startswith(('🕳️ Rabbitholing on', '🧶 Looming forward')):
                        continue
                    # Use display text if available, otherwise use content
                    display_text = msg.get('display', msg['content'])
                    text_area.insert('end', f"\n{display_text}\n")
                else:
                    text_area.insert('end', f"\n{msg.get('model', 'AI')}: {msg.get('display', msg['content'])}\n")
            else:
                text_area.insert('end', f"\n{msg}\n")
        text_area.see('end')

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

    def show_context_menu(self, event):
        """Show the context menu on right-click if text is selected"""
        try:
            if self.text_area.tag_ranges("sel"):  # If there's a selection
                self.context_menu.post(event.x_root, event.y_root)
        except tk.TclError:
            pass
    
    def on_selection(self, event):
        """Handle text selection events"""
        try:
            if self.text_area.tag_ranges("sel"):
                selected_text = self.text_area.get("sel.first", "sel.last")
                print(f"Selected text: {selected_text}")  # For debugging
        except tk.TclError:
            pass
    
    def branch_from_selection(self):
        """Create a new conversation branch from the selected text"""
        try:
            if self.text_area.tag_ranges("sel"):
                selected_text = self.text_area.get("sel.first", "sel.last")
                # Store the selection position for context
                selection_index = self.text_area.index("sel.first")
                print(f"Branching from: {selected_text} at position {selection_index}")
                # TODO: Implement branching logic
                self.create_branch(selected_text, selection_index)
        except tk.TclError:
            pass
    
    def create_branch(self, selected_text, selection_index, parent_branch=None):
        """Create a new branch in the conversation"""
        try:
            # Generate a unique branch ID
            branch_id = f"branch_{len(self.branch_conversations)}"
            
            # Determine parent and context
            if self.active_branch:
                # If we're creating a branch from within a branch
                parent_id = self.active_branch
                parent_data = self.branch_conversations[self.active_branch]
                main_text = self.text_area.get('1.0', f"{selection_index} lineend")
                parent_depth = int(self.branch_tree_view.item(parent_id)['values'][1])
                branch_depth = parent_depth + 1
            else:
                # If we're creating a branch from the main conversation
                parent_id = 'main'
                main_text = self.text_area.get('1.0', f"{selection_index} lineend")
                branch_depth = 1
            
            # Store branch data
            self.branch_conversations[branch_id] = {
                'history': main_text,
                'selected_text': selected_text,
                'conversation': [],
                'turn_count': 0,
                'parent_id': parent_id,
                'depth': branch_depth,
                'children': []
            }
            
            # Update parent's children list
            if parent_id != 'main':
                self.branch_conversations[parent_id]['children'].append(branch_id)
            
            # Add visual branch node
            icon = '↳' if branch_depth == 1 else '└'
            self.branch_tree_view.insert(
                parent_id, 'end', branch_id,
                text=icon,
                values=(selected_text[:50] + "..." if len(selected_text) > 50 else selected_text, str(branch_depth)),
                tags=('branch',)
            )
            
            # Expand parent node and select new branch
            self.branch_tree_view.item(parent_id, open=True)
            self.branch_tree_view.selection_set(branch_id)
            self.branch_tree_view.see(branch_id)
            
            # Switch to this branch immediately
            self.active_branch = branch_id
            self.update_branch_visuals()
            
            # Add initial message and display it
            self.branch_conversations[branch_id]['conversation'].append({
                "role": "user",
                "content": f"Let's explore and expand upon the concept of '{selected_text}' from our previous discussion.",
                "display": f"🕳️ Rabbitholing on '{selected_text}'"
            })
            self.display_conversation(
                self.branch_conversations[branch_id]['conversation'],
                self.text_area
            )
            
            # Start processing in a separate thread
            self.start_loading()
            thread = threading.Thread(target=self.process_branch_conversation, args=(branch_id,))
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            print(f"Error creating branch: {e}")
            self.append_text(f"\nError creating branch: {str(e)}\n")

    def get_all_tree_items(self, parent=''):
        """Get all items in the tree recursively"""
        items = list(self.branch_tree_view.get_children(parent))
        for item in items.copy():
            items.extend(self.get_all_tree_items(item))
        return items

    def update_branch_visuals(self):
        """Update visual indicators for all branches"""
        # Remove active tag from all items
        for item in self.get_all_tree_items():
            tags = list(self.branch_tree_view.item(item)['tags'])
            if 'active' in tags:
                tags.remove('active')
            self.branch_tree_view.item(item, tags=tags)
        
        # Add active tag to current branch
        if self.active_branch:
            current_tags = list(self.branch_tree_view.item(self.active_branch)['tags'])
            if 'active' not in current_tags:
                current_tags.append('active')
            self.branch_tree_view.item(self.active_branch, tags=current_tags)
            
            # Ensure the active branch is visible
            self.branch_tree_view.see(self.active_branch)
            
            # Expand all parent nodes to make the branch visible
            parent = self.branch_conversations[self.active_branch]['parent_id']
            while parent != 'main':
                self.branch_tree_view.item(parent, open=True)
                if parent in self.branch_conversations:
                    parent = self.branch_conversations[parent]['parent_id']
                else:
                    break
            # Ensure main is also expanded
            self.branch_tree_view.item('main', open=True)

    def on_branch_select(self, event):
        """Handle branch selection in tree view"""
        selected_item = self.branch_tree_view.selection()[0]
        if selected_item == 'main':
            # Switch to main conversation
            self.active_branch = None
            self.display_conversation(self.conversation, self.text_area)
        else:
            # Switch to selected branch
            branch_data = self.branch_conversations.get(selected_item)
            if branch_data:
                self.active_branch = selected_item
                self.display_conversation(branch_data['conversation'], self.text_area)
        
        # Update visual indicators
        self.update_branch_visuals()

    def get_branch_path(self, branch_id):
        """Get the full path of branch names from root to the given branch"""
        path = []
        current_id = branch_id
        while current_id != 'main':
            branch_data = self.branch_conversations.get(current_id)
            if not branch_data:
                break
            path.append(branch_data['selected_text'])
            current_id = branch_data['parent_id']
        path.append('Main Conversation')
        return ' → '.join(reversed(path))

    def loom_from_selection(self):
        """Create a new conversation branch that continues forward from the selected text"""
        try:
            if self.text_area.tag_ranges("sel"):
                selected_text = self.text_area.get("sel.first", "sel.last")
                selection_index = self.text_area.index("sel.first")
                print(f"Looming from: {selected_text} at position {selection_index}")
                self.create_loom(selected_text, selection_index)
        except tk.TclError:
            pass

    def create_loom(self, selected_text, selection_index, parent_branch=None):
        """Create a new branch that continues the conversation forward from the selected point"""
        try:
            # Generate a unique branch ID
            branch_id = f"loom_{len(self.branch_conversations)}"
            
            # Determine parent and context
            if self.active_branch:
                parent_id = self.active_branch
                parent_data = self.branch_conversations[self.active_branch]
                main_text = self.text_area.get('1.0', f"{selection_index} lineend")
                parent_depth = int(self.branch_tree_view.item(parent_id)['values'][1])
                branch_depth = parent_depth + 1
            else:
                parent_id = 'main'
                main_text = self.text_area.get('1.0', f"{selection_index} lineend")
                branch_depth = 1
            
            # Store branch data
            self.branch_conversations[branch_id] = {
                'history': main_text,
                'selected_text': selected_text,
                'conversation': [],
                'turn_count': 0,
                'parent_id': parent_id,
                'depth': branch_depth,
                'children': [],
                'type': 'loom'  # Mark this as a loom branch
            }
            
            # Update parent's children list
            if parent_id != 'main':
                self.branch_conversations[parent_id]['children'].append(branch_id)
            
            # Add visual branch node with loom icon
            icon = '↬' if branch_depth == 1 else '⇢'
            self.branch_tree_view.insert(
                parent_id, 'end', branch_id,
                text=icon,
                values=(f"Loom: {selected_text[:40]}..." if len(selected_text) > 40 else f"Loom: {selected_text}", str(branch_depth)),
                tags=('branch', 'loom')
            )
            
            # Configure loom branch style
            self.branch_tree_view.tag_configure('loom', foreground=self.colors['accent'])
            
            # Expand parent node and select new branch
            self.branch_tree_view.item(parent_id, open=True)
            self.branch_tree_view.selection_set(branch_id)
            self.branch_tree_view.see(branch_id)
            
            # Switch to this branch immediately
            self.active_branch = branch_id
            self.update_branch_visuals()
            
            # Add initial message and display it
            self.branch_conversations[branch_id]['conversation'].append({
                "role": "user",
                "content": f"Complete this thought or sentence naturally, continuing forward from exactly this point: '{selected_text}'",
                "display": f"🧶 Looming forward from '{selected_text}'"
            })
            self.display_conversation(
                self.branch_conversations[branch_id]['conversation'],
                self.text_area
            )
            
            # Start processing in a separate thread
            self.start_loading()
            thread = threading.Thread(target=self.process_branch_conversation, args=(branch_id,))
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            print(f"Error creating loom: {e}")
            self.append_text(f"\nError creating loom: {str(e)}\n")

def create_gui():
    root = tk.Tk()
    return AIGUI(root)

def run_gui(gui):
    gui.master.mainloop()