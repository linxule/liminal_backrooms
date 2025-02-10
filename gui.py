# gui.py

from config import (
    TURN_DELAY,
    AI_MODELS,
    SYSTEM_PROMPT_PAIRS,
    SHOW_CHAIN_OF_THOUGHT_IN_CONTEXT
)

import os
from datetime import datetime
from PIL import Image, ImageEnhance, ImageTk
import tkinter as tk
from tkinter import scrolledtext, ttk, filedialog
import requests
from io import BytesIO
import threading
import shutil
import math
import random  # Added import for random angles

class NetworkView(tk.Canvas):
    def __init__(self, master, colors, **kwargs):
        # Enable DPI awareness
        self.scaling = self.get_scaling_factor()
        scaled_kwargs = {k: v * self.scaling if isinstance(v, (int, float)) else v 
                        for k, v in kwargs.items()}
        
        super().__init__(master, **scaled_kwargs)
        self.colors = colors
        self.nodes = {}
        self.selected_node = None
        self.node_radius = 12 * self.scaling  # Reduced base radius
        self.spacing_x = 80 * self.scaling    # Reduced spacing
        self.spacing_y = 60 * self.scaling
        self.padding = 25 * self.scaling
        
        # Add organic movement
        self.time = 0
        self.wave_amplitude = 1.0 * self.scaling
        self.wave_frequency = 0.05
        
        # Modern color scheme aligned with main UI
        self.node_colors = {
            'main': '#569CD6',      # Soft blue (accent color)
            'branch': '#D4D4D4',    # Light grey (text color)
            'loom': '#4E8CC2',      # Darker blue (accent hover)
        }
        
        # Add depth tracking
        self.depth_map = {'main': 0}
        
        # Bind events
        self.bind('<Button-1>', self.on_click)
        self.bind('<B1-Motion>', self.on_drag)
        self.bind('<ButtonRelease-1>', self.on_release)
        self.bind('<Configure>', self.on_resize)
        
        # Animation
        self.animation_active = False
        self.velocity = {}
        
        # Start organic movement
        self.animate_organic_movement()
        
    def get_scaling_factor(self):
        """Get the DPI scaling factor for the current display"""
        try:
            # Try to get system DPI scaling
            return self.winfo_fpixels('1i') / 72.0
        except:
            return 1.5  # Default to 150% scaling if can't detect
        
    def animate_organic_movement(self):
        """Create subtle organic movement in the network"""
        self.time += 0.1
        if len(self.nodes) > 0:
            self.redraw()
        self.after(50, self.animate_organic_movement)
        
    def get_organic_offset(self, node_id):
        """Calculate organic movement offset for a node"""
        depth = self.depth_map.get(node_id, 0)
        x_offset = math.sin(self.time * self.wave_frequency + depth) * self.wave_amplitude
        y_offset = math.cos(self.time * self.wave_frequency + depth) * self.wave_amplitude
        return x_offset, y_offset
        
    def draw_node(self, x, y, node_id, node):
        """Draw a simplified node with just icon and label"""
        color = self.node_colors[node['type'] if node['type'] in self.node_colors else 'branch']
        is_selected = node_id == self.selected_node
        
        # Icon only - using ⦿ for hole (more centered than 🕳️)
        icon = '🍄' if node['type'] == 'main' else '🧶' if node['type'] == 'loom' else '⦿'
        
        # Draw icon
        self.create_text(
            x, y,
            text=icon,
            font=('Segoe UI', int(12 * self.scaling)),
            fill=color
        )
        
        # Small label below with bold if selected
        if node['label']:
            label = node['label'][:15] + '...' if len(node['label']) > 15 else node['label']
            self.create_text(
                x, y + self.node_radius + 5 * self.scaling,
                text=label,
                font=('Segoe UI Bold' if is_selected else 'Segoe UI', int(7 * self.scaling)),
                fill=color
            )
            
    def draw_mycelial_connection(self, start_x, start_y, end_x, end_y, node_type):
        """Draw a simplified connection line"""
        # Single clean line with appropriate style
        self.create_line(
            start_x, start_y,
            end_x, end_y,
            fill=self.node_colors[node_type if node_type in self.node_colors else 'branch'],
            width=1 * self.scaling,
            dash=(6, 4) if node_type == 'loom' else None,
            capstyle=tk.ROUND,
            joinstyle=tk.ROUND
        )
        
    def redraw(self):
        self.delete('all')
        
        # Draw connections first
        for node_id, node in self.nodes.items():
            if node['parent']:
                parent = self.nodes[node['parent']]
                # Get organic offsets
                x_off1, y_off1 = self.get_organic_offset(node_id)
                x_off2, y_off2 = self.get_organic_offset(node['parent'])
                
                self.draw_mycelial_connection(
                    node['x'] + x_off1, node['y'] + y_off1,
                    parent['x'] + x_off2, parent['y'] + y_off2,
                    node['type']
                )
        
        # Draw nodes
        for node_id, node in self.nodes.items():
            x_off, y_off = self.get_organic_offset(node_id)
            self.draw_node(
                node['x'] + x_off,
                node['y'] + y_off,
                node_id,
                node
            )

    def add_node(self, node_id, label, node_type="branch", parent_id=None):
        if parent_id and parent_id in self.nodes:
            parent = self.nodes[parent_id]
            # Use random angle between 0 and 2π (full circle)
            angle = random.uniform(0, 2 * math.pi)
            distance = self.spacing_x * 2.0  # Keep the double distance for spacing
            
            x = parent['x'] + math.cos(angle) * distance
            y = parent['y'] + math.sin(angle) * distance
            
            # Calculate depth based on parent
            self.depth_map[node_id] = self.depth_map.get(parent_id, 0) + 1
        else:
            # Root node position - center of canvas
            x = self.winfo_width() / 2
            y = self.winfo_height() / 2
            self.depth_map[node_id] = 0
            
        self.nodes[node_id] = {
            'x': x, 'y': y,
            'label': label,
            'type': node_type,
            'parent': parent_id,
            'children': [],
            'depth': self.depth_map[node_id]
        }
        
        if parent_id:
            self.nodes[parent_id]['children'].append(node_id)
            
        # Apply stronger initial separation
        self.apply_initial_separation(node_id)
        self.start_animation()
        self.redraw()
        
    def apply_initial_separation(self, new_node_id):
        """Apply stronger initial separation force"""
        new_node = self.nodes[new_node_id]
        
        # Initialize velocity for the new node
        self.velocity[new_node_id] = {'dx': 0, 'dy': 0}
        
        # Apply much stronger initial repulsion
        for node_id, node in self.nodes.items():
            if node_id != new_node_id:
                dx = new_node['x'] - node['x']
                dy = new_node['y'] - node['y']
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < self.spacing_x * 2:  # Increased check distance
                    # Much stronger initial force
                    force = 8000 / (dist * dist) if dist > 1 else 8000
                    self.velocity[new_node_id]['dx'] += (dx / dist) * force
                    self.velocity[new_node_id]['dy'] += (dy / dist) * force
        
        # Apply the initial velocity with larger step
        new_node['x'] += self.velocity[new_node_id]['dx'] * 0.2  # Increased step size
        new_node['y'] += self.velocity[new_node_id]['dy'] * 0.2
        
    def remove_node(self, node_id):
        if node_id in self.nodes:
            node = self.nodes[node_id]
            if node['parent']:
                parent = self.nodes[node['parent']]
                parent['children'].remove(node_id)
            for child_id in node['children']:
                self.remove_node(child_id)
            del self.nodes[node_id]
            self.redraw()
            
    def start_animation(self):
        if not self.animation_active:
            self.animation_active = True
            self.animate()
            
    def animate(self):
        if not self.animation_active:
            return
            
        # Apply force-directed layout
        self.apply_forces()
        self.redraw()
        
        # Continue animation
        self.after(16, self.animate)  # ~60 FPS
        
    def apply_forces(self):
        # Initialize velocities
        self.velocity = {node_id: {'dx': 0, 'dy': 0} for node_id in self.nodes}
        
        # Apply repulsive forces between all nodes
        for n1 in self.nodes:
            for n2 in self.nodes:
                if n1 != n2:
                    self.apply_repulsion(n1, n2)
                    
        # Apply attractive forces along edges
        for node_id, node in self.nodes.items():
            if node['parent']:
                self.apply_attraction(node_id, node['parent'])
                
        # Update positions with boundary constraints
        for node_id in self.nodes:
            # Apply velocity
            self.nodes[node_id]['x'] += self.velocity[node_id]['dx']
            self.nodes[node_id]['y'] += self.velocity[node_id]['dy']
            
            # Constrain to canvas bounds
            self.nodes[node_id]['x'] = max(self.padding, min(self.winfo_width() - self.padding, self.nodes[node_id]['x']))
            self.nodes[node_id]['y'] = max(self.padding, min(self.winfo_height() - self.padding, self.nodes[node_id]['y']))
            
            # If this is the main node, keep it centered horizontally
            if node_id == 'main':
                self.nodes[node_id]['x'] = self.winfo_width() / 2
                
    def apply_repulsion(self, n1, n2):
        node1 = self.nodes[n1]
        node2 = self.nodes[n2]
        dx = node1['x'] - node2['x']
        dy = node1['y'] - node2['y']
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < 1: dist = 1
        
        # Stronger base repulsion force
        force = 5000 / (dist * dist)  # Increased from 3000 to 5000
        
        # Extra repulsion when nodes are too close
        if dist < self.spacing_x:
            force *= 2.0  # Double the force for close nodes
        
        # Apply force with dampening based on depth difference
        depth_diff = abs(self.depth_map[n1] - self.depth_map[n2])
        force *= max(0.5, 1.0 - (depth_diff * 0.2))
        
        self.velocity[n1]['dx'] += (dx / dist) * force
        self.velocity[n1]['dy'] += (dy / dist) * force
        self.velocity[n2]['dx'] -= (dx / dist) * force
        self.velocity[n2]['dy'] -= (dy / dist) * force
        
    def apply_attraction(self, n1, n2):
        node1 = self.nodes[n1]
        node2 = self.nodes[n2]
        dx = node2['x'] - node1['x']
        dy = node2['y'] - node1['y']
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < 1: dist = 1
        
        force = (dist - self.spacing_x) * 0.05  # Spring force
        self.velocity[n1]['dx'] += (dx / dist) * force
        self.velocity[n1]['dy'] += (dy / dist) * force
        self.velocity[n2]['dx'] -= (dx / dist) * force
        self.velocity[n2]['dy'] -= (dy / dist) * force
        
    def on_click(self, event):
        self.selected_node = self.find_node_at(event.x, event.y)
        self.redraw()
        if self.selected_node:
            self.event_generate('<<NodeSelected>>')
            
    def on_drag(self, event):
        if self.selected_node:
            # Constrain dragging within bounds
            x = max(self.padding, min(event.x, self.winfo_width() - self.padding))
            y = max(self.padding, min(event.y, self.winfo_height() - self.padding))
            
            # Don't allow dragging main node horizontally
            if self.selected_node == 'main':
                x = self.winfo_width() / 2
                
            self.nodes[self.selected_node]['x'] = x
            self.nodes[self.selected_node]['y'] = y
            self.redraw()
            
    def on_release(self, event):
        if self.selected_node:
            self.start_animation()
            
    def on_resize(self, event):
        # Update main node position on resize
        if 'main' in self.nodes:
            self.nodes['main']['x'] = self.winfo_width() / 2
            self.nodes['main']['y'] = self.winfo_height() / 2
        self.redraw()
        
    def find_node_at(self, x, y):
        for node_id, node in self.nodes.items():
            dx = x - node['x']
            dy = y - node['y']
            if math.sqrt(dx * dx + dy * dy) <= self.node_radius:
                return node_id
        return None

    def get_node_depth(self, node_id):
        """Get the depth of a node in the tree"""
        if node_id not in self.nodes:
            return 0
        depth = 0
        current = node_id
        while self.nodes[current]['parent']:
            depth += 1
            current = self.nodes[current]['parent']
        return depth

class AIGUI:
    def __init__(self, master):
        self.master = master
        self.conversation = []
        self.turn_count = 0
        self.images = []
        self.image_paths = []
        
        # Modern color scheme
        self.colors = {
            'bg': '#1E1E1E',           # Dark background
            'text_bg': '#252526',      # Slightly lighter background for text
            'text_fg': '#D4D4D4',      # Light grey text
            'input_bg': '#2D2D2D',     # Input background
            'input_fg': '#D4D4D4',     # Input text
            'accent': '#569CD6',       # Soft blue accent
            'accent_hover': '#4E8CC2', # Darker blue for hover
            'button_bg': '#2D2D2D',    # Button background
            'border': '#3E3E42',       # Border color
            'highlight': '#569CD6',    # Selection highlight
            'label_fg': '#D4D4D4',     # Label text
            'status_fg': '#569CD6',    # Status text
            'selected_bg': '#37373D'   # Selection background
        }
        
        # Add branch tracking
        self.branch_conversations = {}  # Store branch conversations by selection_index
        self.active_branch = None      # Currently displayed branch
        self.branch_tree = {}          # Tree structure of branches
        master.title("liminal_backrooms v0.5")
        
        # Configure window for full screen and resizing
        master.geometry("1600x900")  # Larger default size for split view
        master.minsize(1200, 800)    # Larger minimum size
        
        # Configure grid weights for proper resizing
        master.grid_rowconfigure(0, weight=1)
        master.grid_columnconfigure(0, weight=2)  # Main content area
        master.grid_columnconfigure(1, weight=3)  # Branch tree area - make wider (3:2 ratio)
        
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
            text="Propagation Network",
            bg=self.colors['bg'],
            fg=self.colors['label_fg'],
            font=('Orbitron', 12)
        )
        self.branch_title.grid(row=0, column=0, pady=(0, 10), sticky='ew')
        
        # Replace tree view with network view
        self.network_view = NetworkView(
            self.right_pane,
            self.colors,
            bg=self.colors['text_bg'],
            highlightthickness=1,
            highlightbackground=self.colors['border']
        )
        self.network_view.grid(row=1, column=0, sticky='nsew')
        
        # Initialize main conversation as root node
        self.network_view.add_node('main', 'Seed', 'main')
        
        # Bind network selection event
        self.network_view.bind('<<NodeSelected>>', self.on_branch_select)
        
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
        
        # Text area with modern styling
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
            font=('Cascadia Code', 10),  # Modern monospace font
            padx=15,
            pady=15,
            relief='flat',
            borderwidth=0,
            selectbackground=self.colors['selected_bg'],
            selectforeground=self.colors['text_fg']
        )
        self.text_area.grid(row=0, column=0, sticky='nsew', padx=1, pady=1)
        
        # Configure text tags for different message types
        self.text_area.tag_configure('bold', font=('Cascadia Code Bold', 10))
        self.text_area.tag_configure('user', foreground='#D4D4D4')  # Light grey
        self.text_area.tag_configure('ai', foreground='#D4D4D4')    # Light grey
        self.text_area.tag_configure('system', foreground='#569CD6') # Soft blue
        self.text_area.tag_configure('emoji', font=('Segoe UI Emoji', 10))
        self.text_area.tag_configure('header', font=('Cascadia Code Bold', 10), foreground='#569CD6')

        # Create right-click context menu
        self.context_menu = tk.Menu(self.master, tearoff=0, bg=self.colors['bg'], fg=self.colors['text_fg'])
        self.context_menu.add_command(
            label="🕳️ Rabbithole",
            command=self.branch_from_selection
        )
        self.context_menu.add_command(
            label="🔱 Fork",
            command=self.fork_from_selection
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
            font=('Cascadia Code', 11),
            relief='flat',
            bd=0
        )
        self.input_field.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=10)
        
        # Submit button with neon effect
        self.submit_button = tk.Button(
            input_frame,
            text="PROPAGATE",
            command=self.submit_input,
            bg=self.colors['accent'],
            fg='white',
            activebackground=self.colors['accent_hover'],
            activeforeground='white',
            relief='flat',
            bd=0,
            padx=20,
            pady=8,
            font=('Cascadia Code', 10),
            cursor='hand2'
        )
        self.submit_button.pack(side=tk.RIGHT, padx=10, pady=10)
        
        # Status bar with cyberpunk styling
        self.status_bar = tk.Label(
            self.main_frame,
            text=">> DORMANT <<",
            bg=self.colors['bg'],
            fg=self.colors['status_fg'],
            bd=1,
            relief=tk.SUNKEN,
            anchor=tk.W,
            padx=10,
            font=('Cascadia Code', 9)
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
                text=f">> {self.loading_chars[self.loading_index]} PROPAGATING {self.loading_chars[(self.loading_index + 2) % 4]} <<",
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
        self.status_bar.config(text=">> DORMANT <<", fg=self.colors['status_fg'])
        self.input_field.config(state='normal')
        self.submit_button.config(state='normal')
        self.input_field.focus_set()
        
    def submit_input(self):
        """Handle input submission for both main conversation and branches"""
        if self.input_callback and not self.loading:
            input_text = self.input_field.get().strip()
            
            # Store the input text before clearing the field
            stored_input = input_text
            
            # Clear the input field
            self.input_field.delete(0, tk.END)
            
            # Get the current conversation based on active branch
            if self.active_branch:
                current_conversation = self.branch_conversations[self.active_branch]
                
                # Add the input to the branch conversation if there is any
                if stored_input:
                    current_conversation['conversation'].append({
                        "role": "user",
                        "content": stored_input
                    })
                    self.display_conversation(current_conversation['conversation'], self.text_area)
                
                # Start processing
                self.start_loading()
                self.process_branch_conversation(self.active_branch)
            else:
                # Handle main conversation
                self.start_loading()
                # Pass the stored input to the callback
                self.input_callback(stored_input)

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
                branch_data['turn_count'] = 0
                # Update the history differently based on branch type
                if branch_data.get('type') == 'fork':
                    # For fork, keep only context up to the selected point plus new conversation
                    branch_data['history'] = branch_data['selected_with_context']
                else:
                    # For rabbithole, keep full updated context
                    branch_data['history'] = self.text_area.get('1.0', tk.END)
            
            # Import ai_turn here to avoid circular imports
            from main import ai_turn
            
            # Get the current prompt pair
            prompt_pair = SYSTEM_PROMPT_PAIRS[self.prompt_pair_var.get()]
            
            # Create different prompts based on branch type
            if branch_data.get('type') == 'fork':
                branch_prompt = (
                    f"The following is the conversation context up to this point:\n\n{branch_data['selected_with_context']}\n\n"
                    f"Continue the conversation naturally from this exact point: '{branch_data['selected_text']}'. "
                    f"Complete the thought or sentence and continue forward as if you were the original speaker. "
                    f"Do not repeat or rephrase the selected text - start immediately with the continuation."
                )
            else:
                branch_prompt = (
                    f"The following is the conversation context up to this point:\n\n{branch_data['history']}\n\n"
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
                            append_to_branch("\n🧶 Loom paused. Click propagate to continue growing.\n")
                        else:
                            append_to_branch("\n🕳️ Branch exploration paused. Click propagate to continue growing.\n")
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
        
        # Configure text tags with more distinct styling
        text_area.tag_configure('bold', font=('Cascadia Code Bold', 10))
        text_area.tag_configure('user', foreground='#569CD6')  # Soft blue for user
        text_area.tag_configure('ai', foreground='#4EC9B0')    # Teal for AI
        text_area.tag_configure('system', foreground='#CE9178') # Soft orange for system
        text_area.tag_configure('emoji', font=('Segoe UI Emoji', 12))  # Larger font for emojis
        text_area.tag_configure('header', font=('Cascadia Code Bold', 10), foreground='#569CD6')
        text_area.tag_configure('chain_of_thought', foreground='#608B4E')  # Green for chain of thought
        text_area.tag_configure('branch_text', foreground='#C586C0')  # Purple for branch text
        
        # If this is a branch conversation, show the context and path
        if self.active_branch:
            branch_data = self.branch_conversations[self.active_branch]
            path = self.get_branch_path(self.active_branch)
            text_area.insert('end', "=== Branch Path: ", 'header')
            text_area.insert('end', f"{path} ===\n\n", 'branch_text')
            text_area.insert('end', "=== Original Conversation Context ===\n\n", 'header')
            text_area.insert('end', branch_data['history'])
            
            # Show different header based on branch type
            if branch_data.get('type') == 'fork':
                text_area.insert('end', "\n\n=== ", 'header')
                text_area.insert('end', "🔱 ", ('emoji', 'branch_text'))
                text_area.insert('end', f"Forking forward from: ", 'header')
                text_area.insert('end', f"'{branch_data['selected_text']}'", 'branch_text')
                text_area.insert('end', " ===\n\n", 'header')
            else:
                text_area.insert('end', "\n\n=== ", 'header')
                text_area.insert('end', "🕳️ ", ('emoji', 'branch_text'))
                text_area.insert('end', f"Rabbitholing down: ", 'header')
                text_area.insert('end', f"'{branch_data['selected_text']}'", 'branch_text')
                text_area.insert('end', " ===\n\n", 'header')
        
        # Display the conversation messages
        for msg in conversation:
            if isinstance(msg, dict):
                if msg["role"] == "user":
                    # Skip the initial branch message since we already showed it in the header
                    if self.active_branch and msg.get('display', '').startswith(('🕳️ Rabbitholing on', '🧶 Looming forward')):
                        continue
                    
                    # Handle user messages
                    text_area.insert('end', "\nYou: ", 'user')
                    
                    # Check if message starts with emoji
                    content = msg.get('display', msg['content'])
                    if any(content.startswith(emoji) for emoji in ['🕳️', '🧶']):
                        emoji_end = 2  # Length of emoji character
                        text_area.insert('end', content[:emoji_end], 'emoji')
                        text_area.insert('end', content[emoji_end:], 'branch_text')
                    else:
                        text_area.insert('end', f"{content}\n", 'user')
                else:
                    # Handle AI messages
                    text_area.insert('end', '\n')  # Line break before
                    
                    # Insert AI attribution ONCE
                    if 'model' in msg:
                        ai_name = "AI-2" if "AI-2" in msg.get('model', '') else "AI-1"
                        text_area.insert('end', f"{ai_name} ({msg['model']}):\n\n", 'header')
                    else:
                        text_area.insert('end', f"{msg.get('model', 'AI')}:\n\n", 'header')
                    
                    # Handle Chain of Thought if present
                    if 'display' in msg and SHOW_CHAIN_OF_THOUGHT_IN_CONTEXT:
                        cot_parts = msg['display'].split('[Final Answer]')
                        if len(cot_parts) > 1:
                            # Display Chain of Thought in green
                            text_area.insert('end', cot_parts[0].strip(), 'chain_of_thought')
                            text_area.insert('end', '\n\n[Final Answer]\n', 'header')
                            text_area.insert('end', cot_parts[1].strip(), 'ai')
                        else:
                            text_area.insert('end', msg['display'], 'ai')
                    else:
                        text_area.insert('end', f"{msg.get('content', '')}\n", 'ai')
            else:
                # Handle plain text messages
                if str(msg).startswith(('🕳️', '🧶')):
                    text_area.insert('end', msg[:2], 'emoji')
                    text_area.insert('end', msg[2:] + '\n', 'branch_text')
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
                parent_id = self.active_branch
                parent_data = self.branch_conversations[self.active_branch]
                # Keep full context including text after selection for rabbitholing
                main_text = self.text_area.get('1.0', 'end')
                # Calculate depth based on network view's depth tracking
                parent_depth = self.network_view.get_node_depth(parent_id)
                branch_depth = parent_depth + 1
            else:
                parent_id = 'main'
                # Keep full context including text after selection for rabbitholing
                main_text = self.text_area.get('1.0', 'end')
                branch_depth = 1
            
            # Store branch data
            self.branch_conversations[branch_id] = {
                'history': main_text,  # Stores full conversation context
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
            
            # Add node to network view
            display_text = selected_text[:40] + "..." if len(selected_text) > 40 else selected_text
            self.network_view.add_node(branch_id, display_text, "branch", parent_id)
            
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
        items = list(self.network_view.nodes.keys())
        for item in items.copy():
            items.extend(self.get_all_tree_items(item))
        return items

    def update_branch_visuals(self):
        """Update visual indicators for branches"""
        self.network_view.selected_node = self.active_branch
        self.network_view.redraw()

    def on_branch_select(self, event):
        """Handle branch selection in network view"""
        selected_node = self.network_view.selected_node
        if selected_node == 'main':
            # Switch to main conversation
            self.active_branch = None
            self.display_conversation(self.conversation, self.text_area)
        else:
            # Switch to selected branch
            branch_data = self.branch_conversations.get(selected_node)
            if branch_data:
                self.active_branch = selected_node
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
        path.append('Seed')
        return ' → '.join(reversed(path))

    def fork_from_selection(self):
        """Create a new conversation branch that continues forward from the selected text"""
        try:
            if self.text_area.tag_ranges("sel"):
                selected_text = self.text_area.get("sel.first", "sel.last")
                selection_index = self.text_area.index("sel.first")
                print(f"Forking from: {selected_text} at position {selection_index}")
                self.create_fork(selected_text, selection_index)
        except tk.TclError:
            pass

    def create_fork(self, selected_text, selection_index, parent_branch=None):
        """Create a new branch that continues the conversation forward from the selected point"""
        try:
            # Generate a unique branch ID
            branch_id = f"fork_{len(self.branch_conversations)}"
            
            # Determine parent and context
            if self.active_branch:
                parent_id = self.active_branch
                parent_data = self.branch_conversations[self.active_branch]
                # Get context up to and including the selected text
                selected_with_context = self.text_area.get('1.0', selection_index) + selected_text
                # Calculate depth based on network view's depth tracking
                parent_depth = self.network_view.get_node_depth(parent_id)
                branch_depth = parent_depth + 1
            else:
                parent_id = 'main'
                # Get context up to and including the selected text
                selected_with_context = self.text_area.get('1.0', selection_index) + selected_text
                branch_depth = 1
            
            # Store branch data
            self.branch_conversations[branch_id] = {
                'history': selected_with_context,  # Use truncated version for history
                'selected_text': selected_text,
                'selected_with_context': selected_with_context,
                'conversation': [],
                'turn_count': 0,
                'parent_id': parent_id,
                'depth': branch_depth,
                'children': [],
                'type': 'fork'  # Mark this as a fork branch
            }
            
            # Update parent's children list
            if parent_id != 'main':
                self.branch_conversations[parent_id]['children'].append(branch_id)
            
            # Add node to network view
            display_text = selected_text[:40] + "..." if len(selected_text) > 40 else selected_text
            self.network_view.add_node(branch_id, display_text, "fork", parent_id)
            
            # Switch to this branch immediately
            self.active_branch = branch_id
            self.update_branch_visuals()
            
            # Add initial message and display it
            self.branch_conversations[branch_id]['conversation'].append({
                "role": "user",
                "content": f"Complete this thought or sentence naturally, continuing forward from exactly this point: '{selected_text}'",
                "display": f"🔱 Forking forward from '{selected_text}'"
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
            print(f"Error creating fork: {e}")
            self.append_text(f"\nError creating fork: {str(e)}\n")

def create_gui():
    root = tk.Tk()
    return AIGUI(root)

def run_gui(gui):
    gui.master.mainloop()