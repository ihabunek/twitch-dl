from twitchdl.entities import Commenter


# Some nice colors taken from
# https://flatuicolors.com/
USER_COLORS = [
    "#16a085",  # GREEN SEA
    "#27ae60",  # NEPHRITIS
    "#2980b9",  # BELIZE HOLE
    "#686de0",  # EXODUS FRUIT
    "#7f8c8d",  # ASBESTOS
    "#9b59b6",  # AMETHYST
    "#be2edd",  # STEEL PINK
    "#c0392b",  # POMEGRANATE
    "#d35400",  # PUMPKIN
    "#e67e22",  # CARROT
    "#e74c3c",  # ALIZARIN
    "#f1c40f",  # SUN FLOWER
]


def get_commenter_color(commenter: Commenter):
    """Return a consistent random color for a commenter"""
    user_color_index = int(commenter["id"]) % len(USER_COLORS)
    return USER_COLORS[user_color_index]
