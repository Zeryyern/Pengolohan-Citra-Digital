import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
import numpy as np
from PIL import Image, ImageTk
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import csv

from utils import load_maybe_gray, load_image, save_rgb, rgb_to_yuv
from enhance import enhance_grayscale
from colorize import (
    solve_channel, sample_seeds_from_channel,
    generate_seeds_from_reference, generate_pseudocolor_seeds_from_colormap
)
from param_sweep import sweep


class ImageProcessorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Enhancement & Colorization Pipeline")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f0f0f0')
        
        # Variables
        self.input_image = None
        self.output_image = None
        self.input_path = tk.StringVar(value="No image loaded")
        self.enhanced_image = None
        self.stages_images = {}  # Store images for visualization
        
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: Main Processing
        self.tab_main = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_main, text="Main Processing")
        self.create_main_tab()
        
        # Tab 2: Parameter Sweep
        self.tab_sweep = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_sweep, text="Parameter Sweep")
        self.create_sweep_tab()
        
        # Tab 3: Results Summary
        self.tab_summary = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_summary, text="Results Summary")
        self.create_summary_tab()
        
        # Tab 4: Visualization
        self.tab_visual = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_visual, text="Visualization")
        self.create_visualization_tab()
    
    # ==================== TAB 1: MAIN PROCESSING ====================
    def create_main_tab(self):
        """Main processing tab with image loading, parameters, and preview."""
        
        # Create main scrollable container
        main_scroll_frame = ttk.Frame(self.tab_main)
        main_scroll_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create canvas for scrolling
        main_canvas = tk.Canvas(main_scroll_frame, bg='#f0f0f0', highlightthickness=0)
        main_scrollbar = ttk.Scrollbar(main_scroll_frame, orient=tk.VERTICAL, command=main_canvas.yview)
        main_scrollable_frame = ttk.Frame(main_canvas)
        
        main_scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        
        main_canvas.create_window((0, 0), window=main_scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=main_scrollbar.set)
        
        main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        main_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Top: Image loading
        load_frame = ttk.LabelFrame(main_scrollable_frame, text="1. Load Image", padding=10)
        load_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(load_frame, text="Browse Image", command=self.load_image).pack(side=tk.LEFT, padx=5)
        ttk.Label(load_frame, textvariable=self.input_path, foreground="blue").pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        # Middle: Parameters
        param_frame = ttk.LabelFrame(main_scrollable_frame, text="2. Enhancement & Colorization Parameters", padding=10)
        param_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Create grid of parameters
        params = [
            ("W (LIP Power)", "w_var", 3.0, 0.0, 10.0),
            ("E (CST Slope)", "e_var", 0.5, 0.0, 2.0),
            ("k_log (Logistic)", "k_log_var", 10.0, 1.0, 50.0),
            ("smooth_sigma (Smoothing)", "smooth_sigma_var", 0.5, 0.0, 5.0),
            ("seed_ratio (Seed %)", "seed_ratio_var", 0.05, 0.01, 0.5),
            ("sigma (Laplacian Weight)", "sigma_var", 5.0, 1.0, 20.0),
        ]
        
        self.param_vars = {}
        for i, (label, var_name, default, min_val, max_val) in enumerate(params):
            row = i // 3
            col = i % 3
            
            frame = ttk.Frame(param_frame)
            frame.grid(row=row, column=col, padx=10, pady=5, sticky=tk.W)
            
            ttk.Label(frame, text=label).pack()
            
            var = tk.DoubleVar(value=default)
            self.param_vars[var_name] = var
            
            scale = ttk.Scale(frame, from_=min_val, to=max_val, variable=var, orient=tk.HORIZONTAL, length=150)
            scale.pack()
            
            value_label = ttk.Label(frame, text=f"{default:.3f}")
            value_label.pack()
            
            def on_scale_change(event, v=var, l=value_label):
                l.config(text=f"{v.get():.3f}")
            
            scale.bind("<Motion>", on_scale_change)
        
        # Reference image option
        ref_frame = ttk.Frame(param_frame)
        ref_frame.grid(row=3, column=0, columnspan=3, sticky=tk.W, padx=10, pady=5)
        
        self.use_ref = tk.BooleanVar(value=False)
        ttk.Checkbutton(ref_frame, text="Use Reference Image", variable=self.use_ref).pack(side=tk.LEFT)
        ttk.Button(ref_frame, text="Browse Reference", command=self.load_reference).pack(side=tk.LEFT, padx=5)
        self.ref_label = ttk.Label(ref_frame, text="None", foreground="gray")
        self.ref_label.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        self.ref_path = None
        
        # Process button
        process_frame = ttk.Frame(main_scrollable_frame)
        process_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(process_frame, text="PROCESS IMAGE", command=self.process_main, width=30).pack(side=tk.LEFT, padx=5)
        ttk.Button(process_frame, text="Save Output", command=self.save_output, width=20).pack(side=tk.LEFT, padx=5)
        
        self.main_status = ttk.Label(process_frame, text="Ready", foreground="green")
        self.main_status.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        # Preview (with pan scrollbars and sliders)
        preview_frame = ttk.LabelFrame(main_scrollable_frame, text="3. Preview", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        preview_canvas_frame = ttk.Frame(preview_frame)
        preview_canvas_frame.pack(fill=tk.BOTH, expand=True)

        # Vertical and horizontal scrollbars
        self.preview_vsb = ttk.Scrollbar(preview_canvas_frame, orient=tk.VERTICAL)
        self.preview_hsb = ttk.Scrollbar(preview_canvas_frame, orient=tk.HORIZONTAL)

        self.canvas_preview = tk.Canvas(preview_canvas_frame, bg='gray', height=400,
                           xscrollcommand=self.preview_hsb.set,
                           yscrollcommand=self.preview_vsb.set)
        self.preview_vsb.config(command=self.canvas_preview.yview)
        self.preview_hsb.config(command=self.canvas_preview.xview)

        self.canvas_preview.grid(row=0, column=0, sticky='nsew')
        self.preview_vsb.grid(row=0, column=1, sticky='ns')
        self.preview_hsb.grid(row=1, column=0, sticky='ew')

        preview_canvas_frame.rowconfigure(0, weight=1)
        preview_canvas_frame.columnconfigure(0, weight=1)

        # Slider controls for panning (0.0 - 1.0 mapped to xview/yview)
        slider_frame = ttk.Frame(preview_frame)
        slider_frame.pack(fill=tk.X, pady=4)
        ttk.Label(slider_frame, text='Pan X:').pack(side=tk.LEFT, padx=4)
        self.preview_h_slider = ttk.Scale(slider_frame, from_=0.0, to=1.0, orient=tk.HORIZONTAL, command=self.preview_on_h_slider)
        self.preview_h_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        ttk.Label(slider_frame, text='Pan Y:').pack(side=tk.LEFT, padx=4)
        self.preview_v_slider = ttk.Scale(slider_frame, from_=0.0, to=1.0, orient=tk.HORIZONTAL, command=self.preview_on_v_slider)
        self.preview_v_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
    
    def load_image(self):
        """Load input image."""
        path = filedialog.askopenfilename(
            title="Select Grayscale or RGB Image",
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.bmp"), ("All Files", "*.*")]
        )
        if path:
            try:
                self.input_image = load_maybe_gray(path)
                self.input_path.set(os.path.basename(path))
                self.display_preview(self.input_image, side="left")
                self.main_status.config(text="Image loaded", foreground="green")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load image: {e}")
    
    def load_reference(self):
        """Load reference image."""
        path = filedialog.askopenfilename(
            title="Select Reference RGB Image",
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.bmp"), ("All Files", "*.*")]
        )
        if path:
            self.ref_path = path
            self.ref_label.config(text=os.path.basename(path), foreground="blue")
    
    def process_main(self):
        """Process image with selected parameters."""
        if self.input_image is None:
            messagebox.showwarning("Warning", "Please load an image first")
            return
        
        try:
            self.main_status.config(text="Processing...", foreground="orange")
            self.root.update()
            
            # Get parameters
            W = self.param_vars['w_var'].get()
            E = self.param_vars['e_var'].get()
            k_log = self.param_vars['k_log_var'].get()
            smooth_sigma = self.param_vars['smooth_sigma_var'].get()
            seed_ratio = self.param_vars['seed_ratio_var'].get()
            sigma = self.param_vars['sigma_var'].get()
            
            # Detect mode
            if isinstance(self.input_image, np.ndarray) and self.input_image.ndim == 2:
                mode = "grayscale"
            else:
                mode = "rgb"
            
            # Process
            if mode == "grayscale":
                Y = self.input_image
                Y_enh = enhance_grayscale(Y, W=W, E=E, k_log=k_log, smooth_sigma=smooth_sigma)
                self.enhanced_image = Y_enh
                self.stages_images['enhanced'] = Y_enh
                
                if self.use_ref.get() and self.ref_path:
                    ref = load_image(self.ref_path)
                    umask, uvals, vmask, vvals = generate_seeds_from_reference(Y_enh, ref, seed_ratio=seed_ratio, rng_seed=0)
                else:
                    umask, uvals, vmask, vvals = generate_pseudocolor_seeds_from_colormap(Y_enh, cmap='viridis', seed_ratio=seed_ratio, rng_seed=0)
                
                U_est = solve_channel(Y_enh, umask, uvals, sigma=sigma)
                V_est = solve_channel(Y_enh, vmask, vvals, sigma=sigma)
                
                from utils import yuv_to_rgb
                self.output_image = yuv_to_rgb(Y_enh, U_est, V_est)
                self.stages_images['original'] = Y
                self.stages_images['colorized'] = self.output_image
                
            else:
                Y, U_true, V_true = rgb_to_yuv(self.input_image)
                Y_enh = enhance_grayscale(Y, W=W, E=E, k_log=k_log, smooth_sigma=smooth_sigma)
                self.enhanced_image = Y_enh
                self.stages_images['enhanced'] = Y_enh
                
                umask, uvals = sample_seeds_from_channel(U_true, seed_ratio=seed_ratio, rng_seed=0)
                vmask, vvals = sample_seeds_from_channel(V_true, seed_ratio=seed_ratio, rng_seed=1)
                U_est = solve_channel(Y_enh, umask, uvals, sigma=sigma)
                V_est = solve_channel(Y_enh, vmask, vvals, sigma=sigma)
                
                from utils import yuv_to_rgb
                self.output_image = yuv_to_rgb(Y_enh, U_est, V_est)
                self.stages_images['original'] = self.input_image
                self.stages_images['colorized'] = self.output_image
            
            self.display_preview(self.output_image, side="right")
            self.main_status.config(text="Processing complete!", foreground="green")
        
        except Exception as e:
            messagebox.showerror("Error", f"Processing failed: {e}")
            self.main_status.config(text=f"Error: {e}", foreground="red")
    
    def save_output(self):
        """Save processed image."""
        if self.output_image is None:
            messagebox.showwarning("Warning", "Please process an image first")
            return
        
        path = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png"), ("All Files", "*.*")]
        )
        if path:
            try:
                save_rgb(path, self.output_image)
                messagebox.showinfo("Success", f"Image saved to {path}")
                self.main_status.config(text="Image saved!", foreground="green")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save: {e}")
    
    def display_preview(self, image, side="left"):
        """Display image preview in canvas."""
        try:
            # Resize for preview
            h, w = image.shape[:2]
            if h > 300 or w > 300:
                scale = min(300/h, 300/w)
                nh, nw = int(h*scale), int(w*scale)
                import cv2
                image_small = cv2.resize(image.astype(np.uint8), (nw, nh))
            else:
                image_small = image.astype(np.uint8)
            
            # Convert to RGB for display
            if image_small.ndim == 2:
                display_img = np.stack([image_small]*3, axis=2)
            else:
                display_img = image_small
            
            # Convert to PhotoImage
            pil_img = Image.fromarray(display_img.astype(np.uint8))
            photo = ImageTk.PhotoImage(pil_img)
            
            # Display on canvas
            self.canvas_preview.delete("all")
            # place image at top-left so canvas can scroll
            self.canvas_preview.create_image(0, 0, anchor='nw', image=photo)
            self.canvas_preview.image = photo  # Keep reference
            # update scrollregion to image bounding box
            self.canvas_preview.configure(scrollregion=self.canvas_preview.bbox("all"))
            # reset sliders to start
            try:
                self.preview_h_slider.set(0.0)
                self.preview_v_slider.set(0.0)
            except Exception:
                pass
        
        except Exception as e:
            print(f"Preview error: {e}")
    
    # ==================== TAB 2: PARAMETER SWEEP ====================
    def create_sweep_tab(self):
        """Parameter sweep tab."""
        
        # Create main scrollable container
        sweep_scroll_frame = ttk.Frame(self.tab_sweep)
        sweep_scroll_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create canvas for scrolling
        sweep_canvas = tk.Canvas(sweep_scroll_frame, bg='#f0f0f0', highlightthickness=0)
        sweep_scrollbar = ttk.Scrollbar(sweep_scroll_frame, orient=tk.VERTICAL, command=sweep_canvas.yview)
        sweep_scrollable_frame = ttk.Frame(sweep_canvas)
        
        sweep_scrollable_frame.bind(
            "<Configure>",
            lambda e: sweep_canvas.configure(scrollregion=sweep_canvas.bbox("all"))
        )
        
        sweep_canvas.create_window((0, 0), window=sweep_scrollable_frame, anchor="nw")
        sweep_canvas.configure(yscrollcommand=sweep_scrollbar.set)
        
        sweep_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sweep_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Input selection
        input_frame = ttk.LabelFrame(sweep_scrollable_frame, text="1. Select Input Image", padding=10)
        input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(input_frame, text="Browse Image", command=self.sweep_load_image).pack(side=tk.LEFT, padx=5)
        self.sweep_input_label = ttk.Label(input_frame, text="None", foreground="gray")
        self.sweep_input_label.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        self.sweep_input_path = None
        
        # Parameter ranges
        ranges_frame = ttk.LabelFrame(sweep_scrollable_frame, text="2. Parameter Ranges", padding=10)
        ranges_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(ranges_frame, text="W values (space-separated):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.sweep_w_entry = ttk.Entry(ranges_frame, width=40)
        self.sweep_w_entry.insert(0, "0 1 2 3 5 10")
        self.sweep_w_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(ranges_frame, text="Seed ratios (space-separated):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.sweep_seed_entry = ttk.Entry(ranges_frame, width=40)
        self.sweep_seed_entry.insert(0, "0.01 0.03 0.05")
        self.sweep_seed_entry.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(ranges_frame, text="Sigma values (space-separated):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.sweep_sigma_entry = ttk.Entry(ranges_frame, width=40)
        self.sweep_sigma_entry.insert(0, "3 5 10")
        self.sweep_sigma_entry.grid(row=2, column=1, padx=5, pady=5)
        
        # Output directory
        ttk.Label(ranges_frame, text="Output directory:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.sweep_output_entry = ttk.Entry(ranges_frame, width=40)
        self.sweep_output_entry.insert(0, "results/param_sweep")
        self.sweep_output_entry.grid(row=3, column=1, padx=5, pady=5)
        
        # Run button
        run_frame = ttk.Frame(sweep_scrollable_frame)
        run_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(run_frame, text="RUN PARAMETER SWEEP", command=self.run_sweep).pack(side=tk.LEFT, padx=5)
        self.sweep_status = ttk.Label(run_frame, text="Ready", foreground="green")
        self.sweep_status.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        # Progress bar
        self.sweep_progress = ttk.Progressbar(sweep_scrollable_frame, mode='indeterminate')
        self.sweep_progress.pack(fill=tk.X, padx=10, pady=5)
        
        # Results display
        results_frame = ttk.LabelFrame(sweep_scrollable_frame, text="Results", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.sweep_text = tk.Text(results_frame, height=15, width=80, wrap=tk.WORD)
        self.sweep_text.pack(fill=tk.BOTH, expand=True)
    
    def sweep_load_image(self):
        """Load image for sweep."""
        path = filedialog.askopenfilename(
            title="Select Grayscale Image for Sweep",
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.bmp"), ("All Files", "*.*")]
        )
        if path:
            self.sweep_input_path = path
            self.sweep_input_label.config(text=os.path.basename(path), foreground="blue")
    
    def run_sweep(self):
        """Run parameter sweep in background thread."""
        if not self.sweep_input_path:
            messagebox.showwarning("Warning", "Please select an image")
            return
        
        def sweep_thread():
            try:
                self.sweep_status.config(text="Running sweep...", foreground="orange")
                self.sweep_progress.start()
                self.sweep_text.delete(1.0, tk.END)
                self.sweep_text.insert(tk.END, "Starting parameter sweep...\n")
                self.root.update()
                
                # Parse parameters
                Ws = [float(x) for x in self.sweep_w_entry.get().split()]
                seeds = [float(x) for x in self.sweep_seed_entry.get().split()]
                sigmas = [float(x) for x in self.sweep_sigma_entry.get().split()]
                outdir = self.sweep_output_entry.get()
                
                self.sweep_text.insert(tk.END, f"Parameters: W={Ws}, seeds={seeds}, sigmas={sigmas}\n")
                self.sweep_text.insert(tk.END, f"Output: {outdir}\n\n")
                self.root.update()
                
                # Run sweep
                sweep(self.sweep_input_path, outdir, Ws=Ws, seeds=seeds, sigmas=sigmas)
                
                self.sweep_text.insert(tk.END, "\n✓ Sweep complete!\n")
                self.sweep_text.insert(tk.END, f"Results saved to {outdir}/results.csv\n")
                
                self.sweep_status.config(text="Sweep complete!", foreground="green")
            
            except Exception as e:
                self.sweep_text.insert(tk.END, f"\n✗ Error: {e}\n")
                self.sweep_status.config(text=f"Error: {e}", foreground="red")
            
            finally:
                self.sweep_progress.stop()
                self.root.update()
        
        # Run in background
        thread = threading.Thread(target=sweep_thread, daemon=True)
        thread.start()
    
    # ==================== TAB 3: RESULTS SUMMARY ====================
    def create_summary_tab(self):
        """Results summary tab."""
        
        # Create main scrollable container
        summary_scroll_frame = ttk.Frame(self.tab_summary)
        summary_scroll_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create canvas for scrolling
        summary_canvas = tk.Canvas(summary_scroll_frame, bg='#f0f0f0', highlightthickness=0)
        summary_scrollbar = ttk.Scrollbar(summary_scroll_frame, orient=tk.VERTICAL, command=summary_canvas.yview)
        summary_scrollable_frame = ttk.Frame(summary_canvas)
        
        summary_scrollable_frame.bind(
            "<Configure>",
            lambda e: summary_canvas.configure(scrollregion=summary_canvas.bbox("all"))
        )
        
        summary_canvas.create_window((0, 0), window=summary_scrollable_frame, anchor="nw")
        summary_canvas.configure(yscrollcommand=summary_scrollbar.set)
        
        summary_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        summary_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # CSV selection
        csv_frame = ttk.LabelFrame(summary_scrollable_frame, text="1. Load Results CSV", padding=10)
        csv_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(csv_frame, text="Browse CSV", command=self.summary_load_csv).pack(side=tk.LEFT, padx=5)
        self.summary_csv_label = ttk.Label(csv_frame, text="None", foreground="gray")
        self.summary_csv_label.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        self.summary_csv_path = None
        
        # Generate button
        gen_frame = ttk.Frame(summary_scrollable_frame)
        gen_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(gen_frame, text="GENERATE SUMMARY", command=self.generate_summary_report).pack(side=tk.LEFT, padx=5)
        self.summary_status = ttk.Label(gen_frame, text="Ready", foreground="green")
        self.summary_status.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        # Results display
        results_frame = ttk.LabelFrame(summary_scrollable_frame, text="Summary Report", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.summary_text = tk.Text(results_frame, height=20, width=100, wrap=tk.WORD, font=("Courier", 9))
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.summary_text.yview)
        self.summary_text.config(yscroll=scrollbar.set)
        
        self.summary_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def summary_load_csv(self):
        """Load CSV file for summary."""
        path = filedialog.askopenfilename(
            title="Select Results CSV",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if path:
            self.summary_csv_path = path
            self.summary_csv_label.config(text=os.path.basename(path), foreground="blue")
    
    def generate_summary_report(self):
        """Generate summary report."""
        if not self.summary_csv_path:
            messagebox.showwarning("Warning", "Please select a CSV file")
            return
        
        try:
            self.summary_status.config(text="Generating...", foreground="orange")
            self.root.update()
            
            self.summary_text.delete(1.0, tk.END)
            
            # Read CSV
            rows = []
            with open(self.summary_csv_path, newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rows.append({
                        'W': float(row['W']),
                        'seed_ratio': float(row['seed_ratio']),
                        'sigma': float(row['sigma']),
                        'PSNR': float(row['PSNR'])
                    })
            
            if len(rows) == 0:
                self.summary_text.insert(tk.END, "No data in CSV.")
                return
            
            # Calculate statistics
            psnrs = [r['PSNR'] for r in rows]
            W_values = sorted(set(r['W'] for r in rows))
            seed_values = sorted(set(r['seed_ratio'] for r in rows))
            sigma_values = sorted(set(r['sigma'] for r in rows))
            
            # Display report
            report = "=" * 80 + "\n"
            report += "PARAMETER SWEEP ANALYSIS SUMMARY\n"
            report += "=" * 80 + "\n\n"
            
            report += f"Total combinations: {len(rows)}\n"
            report += f"W values: {W_values}\n"
            report += f"Seed ratios: {seed_values}\n"
            report += f"Sigma values: {sigma_values}\n\n"
            
            report += f"PSNR Statistics:\n"
            report += f"  Min:    {min(psnrs):.4f} dB\n"
            report += f"  Max:    {max(psnrs):.4f} dB\n"
            report += f"  Mean:   {np.mean(psnrs):.4f} dB\n"
            report += f"  StdDev: {np.std(psnrs):.4f} dB\n"
            report += f"  Median: {np.median(psnrs):.4f} dB\n\n"
            
            best_idx = np.argmax(psnrs)
            best_row = rows[best_idx]
            report += "=" * 80 + "\n"
            report += "BEST PARAMETERS:\n"
            report += f"  W:          {best_row['W']:.1f}\n"
            report += f"  seed_ratio: {best_row['seed_ratio']:.3f}\n"
            report += f"  sigma:      {best_row['sigma']:.1f}\n"
            report += f"  PSNR:       {best_row['PSNR']:.4f} dB\n"
            report += "=" * 80 + "\n\n"
            
            report += "TOP 5 COMBINATIONS:\n"
            top_5_indices = np.argsort(psnrs)[-5:][::-1]
            for rank, idx in enumerate(top_5_indices, 1):
                r = rows[idx]
                report += f"  {rank}. W={r['W']:>2.0f}, seed={r['seed_ratio']:.3f}, sigma={r['sigma']:>2.0f} → PSNR={r['PSNR']:.4f} dB\n"
            
            self.summary_text.insert(tk.END, report)
            self.summary_status.config(text="Report generated!", foreground="green")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate report: {e}")
            self.summary_status.config(text=f"Error: {e}", foreground="red")
    
    # ==================== TAB 4: VISUALIZATION ====================
    def create_visualization_tab(self):
        """Visualization tab showing image progression through pipeline stages."""
        
        # Create main scrollable container
        viz_scroll_frame = ttk.Frame(self.tab_visual)
        viz_scroll_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create canvas for scrolling
        viz_canvas_scroll = tk.Canvas(viz_scroll_frame, bg='#f0f0f0', highlightthickness=0)
        viz_scrollbar = ttk.Scrollbar(viz_scroll_frame, orient=tk.VERTICAL, command=viz_canvas_scroll.yview)
        viz_scrollable_frame = ttk.Frame(viz_canvas_scroll)
        
        viz_scrollable_frame.bind(
            "<Configure>",
            lambda e: viz_canvas_scroll.configure(scrollregion=viz_canvas_scroll.bbox("all"))
        )
        
        viz_canvas_scroll.create_window((0, 0), window=viz_scrollable_frame, anchor="nw")
        viz_canvas_scroll.configure(yscrollcommand=viz_scrollbar.set)
        
        viz_canvas_scroll.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        viz_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Top: Stage selector with slider
        control_frame = ttk.LabelFrame(viz_scrollable_frame, text="Image Stage Selection", padding=10)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(control_frame, text="Pipeline Stage:").pack(side=tk.LEFT, padx=5)
        
        self.stage_var = tk.StringVar(value="original")
        stages_list = [("Original (Input)", "original"), 
                       ("Enhanced (Y channel)", "enhanced"), 
                       ("Colorized (Output)", "colorized")]
        
        for label, value in stages_list:
            ttk.Radiobutton(control_frame, text=label, variable=self.stage_var, 
                          value=value, command=self.update_visualization).pack(side=tk.LEFT, padx=5)
        
        # OR use slider approach
        ttk.Label(control_frame, text="Stage Slider:").pack(side=tk.LEFT, padx=20)
        self.stage_slider = ttk.Scale(control_frame, from_=0, to=2, orient=tk.HORIZONTAL, 
                                      command=self.on_slider_change, length=200)
        self.stage_slider.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.slider_label = ttk.Label(control_frame, text="Original")
        self.slider_label.pack(side=tk.LEFT, padx=5)
        
        # Main image display (with pan scrollbars and sliders)
        image_frame = ttk.LabelFrame(viz_scrollable_frame, text="Current Stage Display", padding=10)
        image_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        viz_canvas_frame = ttk.Frame(image_frame)
        viz_canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.viz_vsb = ttk.Scrollbar(viz_canvas_frame, orient=tk.VERTICAL)
        self.viz_hsb = ttk.Scrollbar(viz_canvas_frame, orient=tk.HORIZONTAL)
        self.viz_canvas = tk.Canvas(viz_canvas_frame, bg='lightgray', height=500,
                       xscrollcommand=self.viz_hsb.set, yscrollcommand=self.viz_vsb.set)
        self.viz_vsb.config(command=self.viz_canvas.yview)
        self.viz_hsb.config(command=self.viz_canvas.xview)

        self.viz_canvas.grid(row=0, column=0, sticky='nsew')
        self.viz_vsb.grid(row=0, column=1, sticky='ns')
        self.viz_hsb.grid(row=1, column=0, sticky='ew')
        viz_canvas_frame.rowconfigure(0, weight=1)
        viz_canvas_frame.columnconfigure(0, weight=1)

        # Sliders for viz canvas panning
        viz_slider_frame = ttk.Frame(viz_scrollable_frame)
        viz_slider_frame.pack(fill=tk.X, pady=4)
        ttk.Label(viz_slider_frame, text='Pan X:').pack(side=tk.LEFT, padx=4)
        self.viz_h_slider = ttk.Scale(viz_slider_frame, from_=0.0, to=1.0, orient=tk.HORIZONTAL, command=self.viz_on_h_slider)
        self.viz_h_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        ttk.Label(viz_slider_frame, text='Pan Y:').pack(side=tk.LEFT, padx=4)
        self.viz_v_slider = ttk.Scale(viz_slider_frame, from_=0.0, to=1.0, orient=tk.HORIZONTAL, command=self.viz_on_v_slider)
        self.viz_v_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        
        # Bottom: Info and CSV results
        info_frame = ttk.LabelFrame(viz_scrollable_frame, text="Processing Info & Results", padding=10)
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(info_frame, text="Load CSV Results", command=self.load_csv_for_viz).pack(side=tk.LEFT, padx=5)
        self.viz_csv_label = ttk.Label(info_frame, text="No CSV loaded", foreground="gray")
        self.viz_csv_label.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        self.viz_csv_path = None
        
        # Parameters display with scrollbar
        info_scroll_frame = ttk.Frame(info_frame)
        info_scroll_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        info_scroll = ttk.Scrollbar(info_scroll_frame, orient=tk.VERTICAL)
        self.viz_info_text = tk.Text(info_scroll_frame, height=6, width=80, wrap=tk.WORD, font=("Courier", 9), yscrollcommand=info_scroll.set)
        info_scroll.config(command=self.viz_info_text.yview)
        
        self.viz_info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        info_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    
    def on_slider_change(self, value):
        """Handle slider change for stage selection."""
        idx = int(float(value))
        stages = [("original", "Original (Input)"), 
                  ("enhanced", "Enhanced (Y channel)"), 
                  ("colorized", "Colorized (Output)")]
        self.stage_var.set(stages[idx][0])
        self.slider_label.config(text=stages[idx][1])
        self.update_visualization()

    def preview_on_h_slider(self, value):
        """Horizontal pan for main preview canvas (value 0.0-1.0)."""
        try:
            f = float(value)
            self.canvas_preview.xview_moveto(f)
        except Exception:
            pass

    def preview_on_v_slider(self, value):
        """Vertical pan for main preview canvas (value 0.0-1.0)."""
        try:
            f = float(value)
            self.canvas_preview.yview_moveto(f)
        except Exception:
            pass
    
    def update_visualization(self):
        """Update visualization based on selected stage."""
        stage = self.stage_var.get()
        
        if stage not in self.stages_images:
            self.viz_canvas.delete("all")
            self.viz_canvas.create_text(300, 250, text=f"No {stage} image available.\nProcess an image in Tab 1 first.", 
                                       font=("Arial", 14), fill="red")
            return
        
        image = self.stages_images[stage]
        
        try:
            # Convert for display
            if image.ndim == 2:  # Grayscale
                display_img = np.stack([image.astype(np.uint8)]*3, axis=2)
            else:
                display_img = image.astype(np.uint8)
            
            # Resize for canvas
            h, w = display_img.shape[:2]
            max_h, max_w = 450, 600
            if h > max_h or w > max_w:
                scale = min(max_h/h, max_w/w)
                nh, nw = int(h*scale), int(w*scale)
                import cv2
                display_img = cv2.resize(display_img, (nw, nh))
            
            # Convert to PhotoImage
            pil_img = Image.fromarray(display_img)
            photo = ImageTk.PhotoImage(pil_img)
            
            # Display on canvas
            self.viz_canvas.delete("all")
            # place image at top-left for scrolling
            self.viz_canvas.create_image(0, 0, anchor='nw', image=photo)
            self.viz_canvas.image = photo  # Keep reference
            self.viz_canvas.configure(scrollregion=self.viz_canvas.bbox("all"))
            try:
                self.viz_h_slider.set(0.0)
                self.viz_v_slider.set(0.0)
            except Exception:
                pass
            
            # Update info text
            info = f"Stage: {stage.upper()}\n"
            info += f"Shape: {image.shape}\n"
            info += f"Data Type: {image.dtype}\n"
            info += f"Range: [{image.min():.1f}, {image.max():.1f}]"
            
            self.viz_info_text.delete(1.0, tk.END)
            self.viz_info_text.insert(tk.END, info)
        
        except Exception as e:
            self.viz_canvas.delete("all")
            self.viz_canvas.create_text(300, 250, text=f"Error displaying image:\n{e}", 
                                       font=("Arial", 12), fill="red")
    
    def load_csv_for_viz(self):
        """Load CSV results for visualization info."""
        path = filedialog.askopenfilename(
            title="Select Results CSV",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if path:
            self.viz_csv_path = path
            self.viz_csv_label.config(text=os.path.basename(path), foreground="blue")
            self.display_csv_summary()
    
    def display_csv_summary(self):
        """Display summary of CSV results."""
        if not self.viz_csv_path:
            return
        
        try:
            rows = []
            with open(self.viz_csv_path, newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rows.append({
                        'W': float(row['W']),
                        'seed_ratio': float(row['seed_ratio']),
                        'sigma': float(row['sigma']),
                        'PSNR': float(row['PSNR'])
                    })
            
            if len(rows) == 0:
                return
            
            psnrs = [r['PSNR'] for r in rows]
            best_idx = np.argmax(psnrs)
            best = rows[best_idx]
            
            info = f"CSV Results Summary:\n"
            info += f"PSNR Range: [{min(psnrs):.2f}, {max(psnrs):.2f}] dB\n"
            info += f"Best: W={best['W']:.0f}, seed={best['seed_ratio']:.3f}, σ={best['sigma']:.0f} → {best['PSNR']:.2f} dB"
            
            self.viz_info_text.delete(1.0, tk.END)
            self.viz_info_text.insert(tk.END, info)
        
        except Exception as e:
            self.viz_info_text.delete(1.0, tk.END)
            self.viz_info_text.insert(tk.END, f"Error reading CSV: {e}")

    def viz_on_h_slider(self, value):
        """Horizontal pan for visualization canvas (value 0.0-1.0)."""
        try:
            f = float(value)
            self.viz_canvas.xview_moveto(f)
        except Exception:
            pass

    def viz_on_v_slider(self, value):
        """Vertical pan for visualization canvas (value 0.0-1.0)."""
        try:
            f = float(value)
            self.viz_canvas.yview_moveto(f)
        except Exception:
            pass


def main():
    root = tk.Tk()
    app = ImageProcessorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
