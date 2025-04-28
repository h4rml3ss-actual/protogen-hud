# draw_utils.py
# Helper functions for drawing HUD widgets

def draw_text(frame, text, position, color):
    import cv2
    from theme import FONT, FONT_SCALE, THICKNESS
    x, y = position
    # Outline
    cv2.putText(frame, text, (x, y), FONT, FONT_SCALE, (0, 0, 0), THICKNESS + 2, cv2.LINE_AA)
    # Foreground
    cv2.putText(frame, text, (x, y), FONT, FONT_SCALE, color, THICKNESS, cv2.LINE_AA)
    # This function draws text on the given frame at the specified position with a colored foreground and a black outline to enhance visibility.

def draw_bar(frame, value, max_value, position, color):
    import cv2
    x, y = position
    bar_width = 200
    bar_height = 20
    # Calculate the fill ratio, clamping between 0 and 1 to avoid overflow or underflow
    fill_ratio = max(0.0, min(value / max_value, 1.0))
    fill_width = int(bar_width * fill_ratio)

    # Draw the background rectangle of the bar (gray color)
    cv2.rectangle(frame, (x, y), (x + bar_width, y + bar_height), (50, 50, 50), -1)
    # Draw the filled portion of the bar based on the current value and color
    cv2.rectangle(frame, (x, y), (x + fill_width, y + bar_height), color, -1)
    # Draw the outline of the bar in white for clear separation
    cv2.rectangle(frame, (x, y), (x + bar_width, y + bar_height), (255, 255, 255), 1)
    # This function draws a horizontal bar representing a value relative to a maximum value, useful for HUD indicators like health or progress.
