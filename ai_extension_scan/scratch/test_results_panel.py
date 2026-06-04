import sys
import os
import time
import threading
import customtkinter as ctk

# Ensure root directory is in python path
sys.path.insert(0, os.path.abspath("."))

from ui import results_panel
from core.checker import CheckResult

def run_test():
    print("Starting CTk root...")
    root = ctk.CTk()
    root.title("renScan UI Test Runner")
    root.geometry("400x300")
    
    # Label to help guide testing
    label = ctk.CTkLabel(root, text="Testing renScan Results Panel UI\n\nClose this window or press Esc on the results\npanel to quit.", font=("Segoe UI", 13))
    label.pack(pady=40)

    # Mock Result with some dummy issues
    mock_result = CheckResult(
        grammar=[
            "Found 'this are' which should be 'this is'. Subject-verb agreement mismatch.",
            "Missing article 'a' in 'bad grammar example'. Should be 'a bad grammar example'."
        ],
        spelling=[
            "Found misspelling: 'Analysing' (UK English). If your setting is US English, change to 'Analyzing'."
        ],
        structure=[
            "Consider breaking down this long sentence into two shorter sentences to improve corporate readability."
        ],
        tone=[
            "The tone is slightly too informal. Consider replacing 'doesn't know shit' with 'may not have technical expertise'."
        ],
        rewrite="This is an example of bad grammar. Our writing assistant is designed to help corporate users who may not have technical expertise, making their lives easier.",
        raw="## GRAMMAR\n- Found 'this are' which should be 'this is'...\n- Missing article 'a'...\n## SPELLING\n- Found misspelling: 'Analysing'...\n## STRUCTURE\n- Consider breaking down...\n## TONE\n- The tone is slightly...\n## REWRITE\nThis is an example of bad grammar..."
    )

    def trigger_panel():
        print("Showing results panel loading screen...")
        root.after(0, results_panel.show_loading)
        
        # Wait 3 seconds to let user see rotating loading messages
        time.sleep(3)
        
        print("Populating results panel with mock data...")
        root.after(0, lambda: results_panel.show(mock_result))

    threading.Thread(target=trigger_panel, daemon=True).start()
    
    root.mainloop()

if __name__ == "__main__":
    run_test()
