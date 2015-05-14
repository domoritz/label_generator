from wand.image import Image
from wand.color import Color


def render_chart(pdf_file, page, bounds, dpi, target):
    pdf_page = pdf_file + '[{}]'.format(page)
    with Image(filename=pdf_page, resolution=dpi) as img:
        factor = 1.0*dpi/100

        x0 = bounds[0]
        y0 = bounds[1]
        w = bounds[2] - x0
        h = bounds[3] - y0

        img.crop(left=int(x0*factor), top=int(y0*factor),
                 width=int(w*factor), height=int(h*factor))

        with Image(width=img.width, height=img.height,
                   background=Color("white")) as bg:
            bg.composite(img, 0, 0)
            bg.save(filename=target)

if __name__ == '__main__':
    render_chart('testdata/paper.pdf', 1,
                 [100, 200, 500, 500], 200, '/tmp/rendered_region_2x.png')
