from datetime import datetime
def _print(*msg):
    print(datetime.now().strftime("%d/%m %H:%M:%S "), msg)
