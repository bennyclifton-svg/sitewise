"""Original outline studies for SiteWise. No third-party font outlines used."""

import math
from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString

OUT = Path(__file__).resolve().parents[3] / 'frontend/public/landing-assets/datum'


def curve(points, steps=16):
    a, b, c, d = points
    return [tuple((1-t)**3*a[j]+3*(1-t)**2*t*b[j]+3*(1-t)*t*t*c[j]+t**3*d[j]
                  for j in (0, 1)) for t in [i/steps for i in range(steps+1)]]


def rounded(x, y, w, h, r):
    result = []
    for cx, cy, start in [(x+w-r,y+h-r,0),(x+r,y+h-r,90),
                          (x+r,y+r,180),(x+w-r,y+r,270)]:
        result += [(cx+r*math.cos(math.radians(start+i*90/12)),
                    cy+r*math.sin(math.radians(start+i*90/12))) for i in range(13)]
    return result+[result[0]]


def stroke(pen, points, thickness):
    # A continuous mitered ribbon makes closed, editable TrueType contours.
    normals=[]
    for a,b in zip(points,points[1:]):
        dx,dy=b[0]-a[0],b[1]-a[1]
        length=math.hypot(dx,dy)
        normals.append((-dy/length,dx/length) if length else (0,0))
    left,right=[],[]
    for i,p in enumerate(points):
        n=normals[min(i,len(normals)-1)]
        if 0<i<len(points)-1:
            previous=normals[i-1]
            denom=max(.3,1+previous[0]*n[0]+previous[1]*n[1])
            n=((previous[0]+n[0])/denom,(previous[1]+n[1])/denom)
        left.append((p[0]+n[0]*thickness/2,p[1]+n[1]*thickness/2))
        right.append((p[0]-n[0]*thickness/2,p[1]-n[1]*thickness/2))
    outline=left+right[::-1]
    pen.moveTo(outline[0])
    for p in outline[1:]: pen.lineTo(p)
    pen.closePath()


def glyphs(radius):
    oval=lambda h=500: rounded(60,30,450,h-60,radius)
    s=lambda h: curve([(510,h-60),(30,h+90),(-30,h*.5),(285,h*.5)])+curve([(285,h*.5),(620,h*.5),(590,-85),(60,60)])[1:]
    c=lambda h: curve([(510,h-65),(-90,h+150),(-90,-150),(510,65)])
    bowl=lambda y,h: curve([(70,y+h),(630,y+h+80),(630,y-80),(70,y)])
    g={
      'a':[oval(),[(510,500),(510,0)]], 'b':[[(60,0),(60,730)],oval()],
      'c':[c(500)], 'd':[oval(),[(510,0),(510,730)]],
      'e':[[(60,255),(510,255)]]+[curve([(510,255),(510,650),(-90,570),(60,100)])+curve([(60,100),(130,-30),(380,-10),(510,65)])[1:]],
      'f':[curve([(140,0),(140,0),(140,560),(140,600)])+curve([(140,600),(140,740),(320,760),(380,710)])[1:],[(30,490),(350,490)]],
      'g':[oval(),[(510,500),(510,-50)]+curve([(510,-50),(510,-250),(180,-240),(80,-160)])[1:]],
      'h':[[(60,0),(60,730)],curve([(60,330),(60,560),(510,580),(510,320)])+[(510,0)]],
      'i':[[(100,0),(100,500)],[(100,645),(100,710)]],
      'j':[[(230,500),(230,-100)]+curve([(230,-100),(230,-220),(90,-220),(30,-170)])[1:],[(230,645),(230,710)]],
      'k':[[(60,0),(60,730)],[(500,500),(60,210)],[(260,340),(520,0)]],
      'l':[[(90,730),(90,0)]],
      'm':[[(60,0),(60,500)],curve([(60,340),(60,550),(330,550),(330,320)])+[(330,0)],curve([(330,340),(330,550),(600,550),(600,320)])+[(600,0)]],
      'n':[[(60,0),(60,500)],curve([(60,330),(60,560),(510,580),(510,320)])+[(510,0)]],
      'o':[oval()], 'p':[[(60,-210),(60,500)],oval()], 'q':[oval(),[(510,500),(510,-210)]],
      'r':[[(60,0),(60,500)],curve([(60,290),(60,500),(260,560),(400,460)])],
      's':[s(500)], 't':[[(150,670),(150,110)]+curve([(150,110),(150,-10),(280,-10),(360,40)])[1:],[(30,500),(350,500)]],
      'u':[[(60,500),(60,180)]+curve([(60,180),(60,-50),(510,-50),(510,180)])[1:]+[(510,500)]],
      'v':[[(50,500),(280,0),(510,500)]], 'w':[[(45,500),(170,0),(335,340),(500,0),(625,500)]],
      'x':[[(60,500),(510,0)],[(510,500),(60,0)]], 'y':[[(50,500),(280,0)],[(510,500),(200,-210)]],
      'z':[[(60,500),(510,500),(60,0),(510,0)]],
      'A':[[(30,0),(285,700),(540,0)],[(120,240),(450,240)]],
      'B':[[(60,0),(60,700)],bowl(355,345),bowl(0,355)],
      'C':[c(700)], 'D':[[(60,0),(60,700)],bowl(0,700)],
      'E':[[(520,700),(60,700),(60,0),(520,0)],[(60,350),(430,350)]],
      'F':[[(60,0),(60,700),(520,700)],[(60,350),(430,350)]],
      'G':[c(700),[(310,300),(510,300),(510,65)]],
      'H':[[(60,0),(60,700)],[(510,0),(510,700)],[(60,350),(510,350)]],
      'I':[[(100,0),(100,700)]], 'J':[[(510,700),(510,180)]+curve([(510,180),(510,-70),(60,-70),(60,180)])[1:]],
      'K':[[(60,0),(60,700)],[(520,700),(60,250)],[(250,440),(540,0)]],
      'L':[[(60,700),(60,0),(520,0)]],
      'M':[[(60,0),(60,700),(345,280),(630,700),(630,0)]],
      'N':[[(60,0),(60,700),(510,0),(510,700)]],
      'O':[oval(700)], 'P':[[(60,0),(60,700)],bowl(330,370)],
      'Q':[oval(700),[(340,170),(570,-70)]], 'R':[[(60,0),(60,700)],bowl(330,370),[(280,330),(540,0)]],
      'S':[s(700)], 'T':[[(30,700),(550,700)],[(290,700),(290,0)]],
      'U':[[(60,700),(60,210)]+curve([(60,210),(60,-70),(510,-70),(510,210)])[1:]+[(510,700)]],
      'V':[[(35,700),(285,0),(535,700)]], 'W':[[(35,700),(185,0),(365,470),(545,0),(695,700)]],
      'X':[[(40,700),(530,0)],[(530,700),(40,0)]], 'Y':[[(30,700),(285,350),(540,700)],[(285,350),(285,0)]],
      'Z':[[(50,700),(520,700),(50,0),(520,0)]],
      '.':[[(90,0),(90,35)]], ',':[[(115,40),(60,-100)]], ':':[[(90,0),(90,35)],[(90,390),(90,425)]],
      '-':[[(40,280),(330,280)]], '/':[[(40,-70),(420,730)]],
      '0':[oval(700)], '1':[[(90,550),(250,700),(250,0)]],
      '2':[curve([(60,570),(60,800),(580,800),(510,520)])+[(60,0),(520,0)]],
      '3':[[(60,700),(510,700),(280,400)]+curve([(280,400),(650,430),(620,-130),(60,40)])[1:]],
      '4':[[(420,0),(420,700),(40,200),(540,200)]],
      '5':[[(510,700),(70,700),(70,390)]+curve([(70,390),(620,570),(660,-160),(60,40)])[1:]],
      '6':[curve([(480,680),(100,830),(-80,130),(130,40)])+curve([(130,40),(650,-150),(650,520),(70,360)])[1:]],
      '7':[[(50,700),(530,700),(220,0)]], '8':[rounded(60,350,450,350,140),rounded(60,0,450,350,140)],
      '9':[curve([(90,20),(470,-130),(650,570),(440,660)])+curve([(440,660),(-80,850),(-80,180),(500,340)])[1:]],
    }
    return g


def build(name, width, weight, radius):
    shapes=glyphs(radius)
    refined=name in ('DatumRefined','DatumSoft')
    if refined:
        shapes['e']=[[(65,265),(510,265)],
                     curve([(510,265),(510,575),(65,575),(65,265)])+
                     curve([(65,265),(65,-15),(365,-15),(500,75)])[1:]]
        shapes['r']=[[(60,0),(60,500)],
                     curve([(60,290),(60,460),(230,535),(365,470)])]
        shapes['W']=[[(35,700),(180,0),(345,440),(510,0),(655,700)]]
    if name=='Span':
        shapes['a']=[curve([(80,430),(450,650),(510,420),(510,0)]),
                     rounded(60,20,450,290,130)]
        shapes['W']=[[(35,700),(160,0),(350,420),(540,0),(665,700)]]
    if name=='Section':
        shapes['S']=[[(520,700),(60,700),(60,370),(510,330),(510,0),(60,0)]]
        shapes['s']=[[(510,490),(60,490),(60,275),(510,225),(510,0),(60,0)]]
    order=['.notdef','space']+[f'uni{ord(c):04X}' for c in shapes]
    fb=FontBuilder(1000,isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap({32:'space',**{ord(c):f'uni{ord(c):04X}' for c in shapes}})
    outlines={}; metrics={}
    for char,paths in [('',[]),(' ',[])]+list(shapes.items()):
        key='.notdef' if char=='' else 'space' if char==' ' else f'uni{ord(char):04X}'
        pen=TTGlyphPen(None)
        for path in paths: stroke(pen,[(x*width+45,y+70) for x,y in path],weight)
        outlines[key]=pen.glyph()
        advance=(max(p[0] for path in paths for p in path)*width+weight/2+110) if paths else 310
        metrics[key]=(round(advance),40)
        if refined and paths:
            glyph=outlines[key]
            glyph.recalcBounds(None)
            left=34 if char in 'ilI' else 40
            glyph.coordinates.translate((left-glyph.xMin,0))
            glyph.recalcBounds(None)
            metrics[key]=(glyph.xMax+left,left)
    fb.setupGlyf(outlines); fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=900,descent=-260)
    fb.setupNameTable({'familyName':f'SiteWise {name}','styleName':'Regular','uniqueFontIdentifier':f'SiteWise-{name}-Study-01',
                      'fullName':f'SiteWise {name} Study','psName':f'SiteWise-{name}-Study',
                      'copyright':'Original SiteWise prototype letterforms. 2026. No third-party outlines.'})
    fb.setupOS2(sTypoAscender=900,sTypoDescender=-260,usWinAscent=950,usWinDescent=300)
    fb.setupPost(); fb.setupMaxp()
    if refined:
        pairs=[('W','i',-28),('S','i',-12),('T','h',-20),('T','o',-42),
               ('A','V',-35),('V','a',-25),('W','a',-24),('r','s',-15),
               ('r','e',-12),('t','h',-10),('S','t',-12)]
        rules=' '.join(f'pos uni{ord(a):04X} uni{ord(b):04X} {v};' for a,b,v in pairs)
        addOpenTypeFeaturesFromString(fb.font,'feature kern { '+rules+' } kern;')
    fb.save(OUT/f'{name}.ttf')
    print(name, len(shapes), 'original glyphs')


if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    for parameters in [('Datum',1.16,62,110),('Span',1.06,55,210),('Section',.94,76,28),
                       ('DatumRefined',1.02,72,145),('DatumSoft',1.02,66,195)]:
        build(*parameters)
