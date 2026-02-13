def display_colored_text(fg_code, fg_name):
    """
    Display a sample text with the specified foreground ANSI color code.

    Parameters:
    fg_code (int): ANSI code for the foreground color (0-255).
    fg_name (str): Name of the foreground color.
    """
    # ANSI escape code for setting text color
    fg_ansi = f"\033[38;5;{fg_code}m"  # Set foreground color
    reset_ansi = "\033[0m"             # Reset to default

    # Sample text to display
    sample_text = f" {fg_name} (Code: {fg_code}) "

    # Display the colored text
    print(f"{fg_ansi}{sample_text}{reset_ansi}")

def preview_foreground_colors():
    """
    Iterate through a list of foreground color codes and names, displaying each.
    """
    # Iterate through all 256 color codes
    for fg_code in range(256):
        fg_name = f"Color {fg_code}"
        display_colored_text(fg_code, fg_name)

def prompt_for_colors():
    # Prompt user for foreground and background color codes
    try:
        fg_code = int(input("Enter foreground color code (0-255): "))
        bg_code = int(input("Enter background color code (0-255): "))

        # Validate input
        if 0 <= fg_code <= 255 and 0 <= bg_code <= 255:
            display_colored_text(fg_code, fg_color_name=bg_code)
        else:
            print("Error: Color codes must be between 0 and 255.")
    except ValueError:
        print("Error: Please enter valid integer values for color codes.")

def display_colored_text(fg_code, fg_color_name="Sample Text"):
    """
    Display a sample text with the specified foreground and background ANSI color codes.

    Parameters:
    fg_code (int): ANSI code for the foreground color (0-255).
    bg_code (int): ANSI code for the background color (0-255).
    """
    # ANSI escape codes for setting text color
    fg_ansi = f"\033[38;5;{fg_code}m"  # Set foreground color
    #bg_ansi = f"\033[48;5;{bg_code}m"  # Set background color
    reset_ansi = "\033[0m"             # Reset to default

    # Display the colored text
    #print(f"{fg_ansi}{bg_ansi}{sample_text}{reset_ansi}")
    print(f"{fg_ansi}{fg_color_name}{reset_ansi}")

if __name__ == "__main__":
    preview_foreground_colors()
    prompt_for_colors()