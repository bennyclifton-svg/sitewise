"""Illustrative two-unit contour intervals. No surveyed elevation is asserted."""
import math
from pathlib import Path

OUTPUT = Path(__file__).resolve().parents[3] / 'frontend/public/landing-assets/coordination/sitewise-contours.svg'


def height(x, y):
    return (22 * math.exp(-((x+170)**2/180000+(y-100)**2/100000))
            + 13 * math.exp(-((x-240)**2/100000+(y+230)**2/150000))
            + .012*y + 3*math.sin(x/190+y/310))


def main():
    paths=[]
    for level in range(-8,41,2):
        runs=[]
        for y in range(-650,650,12):
            for x in range(-550,550,12):
                points=[(x,y),(x+12,y),(x+12,y+12),(x,y+12)]
                values=[height(*p) for p in points]
                hits=[]
                for i,j in [(0,1),(1,2),(2,3),(3,0)]:
                    if (values[i]<level)!=(values[j]<level):
                        t=(level-values[i])/(values[j]-values[i])
                        hits.append((points[i][0]+t*(points[j][0]-points[i][0]),points[i][1]+t*(points[j][1]-points[i][1])))
                for i in range(0,len(hits)-1,2):
                    a,b=hits[i:i+2]
                    runs.append(f'M{a[0]:.1f},{a[1]:.1f}L{b[0]:.1f},{b[1]:.1f}')
        style='index' if level%10==0 else 'minor'
        paths.append(f'<path d="{" ".join(runs)}" class="{style}"/>')
    OUTPUT.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="-280 -360 560 720" fill="none"><title>Illustrative terrain contours</title><style>path{stroke:#7397cf;stroke-width:.55;vector-effect:non-scaling-stroke}.index{stroke-width:.9}</style>'+''.join(paths)+'</svg>')


if __name__=='__main__':
    main()
