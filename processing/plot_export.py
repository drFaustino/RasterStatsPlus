import os

def save_histogram(figure, path, dpi=300):
    ext = os.path.splitext(path)[1].lower()

    if ext == ".png":
        figure.savefig(path, dpi=dpi, format="png")
    elif ext == ".svg":
        figure.savefig(path, format="svg")
    else:
        raise ValueError("Formato non supportato. Usa .png o .svg")
