# ruff: noqa
"""Pink Floyd prism: colour style, no dependencies."""

A, B, C = (319, 68), (218, 241), (415, 241)
ENTRY = (273, 147)
TOP, BOTTOM = (355, 131), (375, 169)
COLORS = [(255, 62, 40), (255, 144, 30), (255, 235, 65),
          (110, 235, 80), (70, 195, 255), (190, 135, 255)]


def inside(x, y, vertices):
    signs = []
    for a, b in zip(vertices, vertices[1:]+vertices[:1]):
        signs.append((b[0]-a[0])*(y-a[1])-(b[1]-a[1])*(x-a[0]))
    return min(signs) >= 0 or max(signs) <= 0


def render(style, width, height):
    return geometric(width, height)


def geometric(width, height):
    canvas = [[' ']*width for _ in range(height)]
    colors = [[(210,230,240)]*width for _ in range(height)]
    def plot(x, y, char, rgb=(210,230,240)):
        if 0 <= x < width and 0 <= y < height:
            canvas[y][x], colors[y][x] = char, rgb
    def point(p):
        return round(p[0]/640*(width-1)), round((p[1]-20)/320*(height-1))
    def stroke(a, b, char, rgb=(210,230,240)):
        x0,y0=point(a); x1,y1=point(b)
        steps=max(abs(x1-x0),abs(y1-y0),1)
        for i in range(steps+1):
            plot(round(x0+(x1-x0)*i/steps),round(y0+(y1-y0)*i/steps),char,rgb)
    for row in range(height):
        for col in range(width):
            x,y=col*640/(width-1),row*320/(height-1)+20
            if inside(x,y,[ENTRY,TOP,BOTTOM]):
                plot(col,row,'.' if x<325 else ':')
            if inside(x,y,[TOP,(640,180),(640,240),BOTTOM]):
                upper=131+(x-355)*49/285
                lower=169+(x-375)*71/265
                band=max(0,min(5,int((y-upper)/(lower-upper)*6)))
                plot(col,row,':=+*#@'[band],COLORS[band])
    stroke(A,B,'/');stroke(A,C,'\\');stroke(B,C,'_')
    stroke((0,215),ENTRY,'-',(255,252,229))
    ax,ay=point(A);plot(ax,ay,'^')
    output=[]
    for chars,rgbs in zip(canvas,colors):
        parts=[]; previous=None
        for char,rgb in zip(chars,rgbs):
            if char!=' ' and rgb!=previous:
                parts.append('\x1b[38;2;%d;%d;%dm'%rgb);previous=rgb
            parts.append(char)
        output.append(''.join(parts).rstrip()+'\x1b[0m')
    return output
