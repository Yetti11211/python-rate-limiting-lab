"""Interactive viewer and video-frame renderer for the actual QueueLab model."""
from pathlib import Path
import math
from PIL import Image, ImageDraw, ImageFont, ImageTk
from model import CASES, run_case

HERE = Path(__file__).resolve().parent
BG = '#0a1220'
INK = '#edf4ff'
MUTED = '#8fa6c3'
COLORS = ['#66ddc3', '#ff866c', '#ffc15a', '#82b8ff']
TRACES = [run_case(case) for case in CASES]
FONT = 'C:/Windows/Fonts/segoeui.ttf'
BOLD = 'C:/Windows/Fonts/segoeuib.ttf'


def ft(size, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size)


def render(case_index, seconds, comparison=False):
    """Same frame function is used by the GUI and the video exporter."""
    image = Image.new('RGB', (1280, 720), BG)
    d = ImageDraw.Draw(image)
    case = CASES[case_index]
    trace = TRACES[case_index]
    idx = min(len(trace)-1, max(0, round(seconds*10)))
    row = trace[idx]
    color = COLORS[case_index]
    d.text((32,20), 'QUEUE LAB  /  PYTHON', font=ft(20,True), fill=color)
    d.text((875,20), 'MODEL TIME  '+f'{row["time"]:04.1f} / 30.0 s',font=ft(19),fill=MUTED)
    d.text((32,61), case.name, font=ft(43,True),fill=INK)
    d.text((32,117), f'{case.arrival_rate} задач/с  →  4 обработчика × 200 мс ожидания',font=ft(23),fill=MUTED)
    if comparison:
        for j,c in enumerate(CASES):
            y=185+j*96;r=TRACES[j][idx]
            d.rounded_rectangle((32,y,1248,y+81),12,fill='#12243a')
            d.text((53,y+12),c.name,font=ft(24,True),fill=COLORS[j])
            d.text((280,y+16),f'Q {r["queued"]:3}',font=ft(28),fill=INK)
            d.text((475,y+16),f'p95 {r["p95_ms"]/1000:.2f} s',font=ft(28),fill=INK)
            d.text((760,y+16),f'OK {r["completed"]}',font=ft(28),fill=INK)
            d.text((1020,y+16),f'DROP {r["rejected"]}',font=ft(24),fill=INK)
        d.text((36,600),'p95 только по завершённым задачам. Смотрите и на отказы.',font=ft(25),fill='#ffc15a')
    else:
        labels=[('В ОЧЕРЕДИ',str(row['queued'])),('ЗАВЕРШЕНО',str(row['completed'])),('ОТКЛОНЕНО',str(row['rejected'])),('p95 ОТВЕТА',f'{row["p95_ms"]/1000:.2f} s')]
        for j,(label,value) in enumerate(labels):
            x=32+j*310;d.rounded_rectangle((x,175,x+286,280),12,fill='#12243a')
            d.text((x+18,191),label,font=ft(17),fill=MUTED)
            d.text((x+18,222),value,font=ft(35,True),fill=color)
        # Every displayed number comes from model.py, including worker state.
        d.text((33,312),'Обработчики ждут условную зависимость',font=ft(22),fill=INK)
        for j in range(4):
            x=35+j*113;busy=j<row['active']
            d.rounded_rectangle((x,353,x+97,425),9,fill=color if busy else '#213248')
            d.text((x+9,368),'WAIT' if busy else 'IDLE',font=ft(21,True),fill=BG if busy else MUTED)
        d.text((35,445),f'В работе: {row["active"]}/4   Просрочено: {row["expired"]}',font=ft(21),fill=MUTED)
        d.text((555,315),'Длина очереди за 30 секунд',font=ft(22),fill=INK)
        x0,y0,w,h=565,375,625,205
        d.line((x0,y0,x0,y0+h,x0+w,y0+h),fill=MUTED,width=2)
        for tick in [0,100,200,300]:
            y=y0+h-tick/320*h
            d.line((x0,y,x0+w,y),fill='#24354c')
            d.text((x0-36,y-9),str(tick),font=ft(14),fill=MUTED)
        pts=[(x0+r['time']/30*w,y0+h-r['queued']/320*h) for r in trace[:idx+1]]
        if len(pts)>1:d.line(pts,fill=color,width=4)
        for n in [0,10,20,30]:d.text((x0+n/30*w-9,y0+h+10),str(n),font=ft(16),fill=MUTED)
        d.text((35,513),'Сохранение задач',font=ft(21,True),fill=INK)
        d.text((35,550),f'{row["generated"]} = {row["completed"]} + {row["queued"]} + {row["active"]}',font=ft(25),fill=INK)
        d.text((35,586),f'      + {row["rejected"]} отклонено + {row["expired"]} просрочено',font=ft(18),fill=MUTED)
    d.text((32,672),'Работающий офлайн-проект • время модельное • CPU и сеть не измеряются',font=ft(18),fill=MUTED)
    return image


def main():
    import tkinter as tk
    root=tk.Tk();root.title('Queue Lab — рабочая модель очереди')
    root.configure(bg=BG)
    controls=tk.Frame(root,bg=BG);controls.pack(fill='x')
    view=tk.Label(root,bg=BG);view.pack()
    current={'case':0,'seconds':0.0,'play':True,'compare':False}
    def choose(i):current.update(case=i,seconds=0.0,play=True,compare=False)
    for i,case in enumerate(CASES):
        tk.Button(controls,text=f'{i+1}  {case.name}',command=lambda i=i:choose(i),font=('Segoe UI',12),bg='#16344c',fg='white').pack(side='left',padx=6,pady=8)
    tk.Button(controls,text='СРАВНЕНИЕ',command=lambda:current.update(compare=True,seconds=0,play=True),font=('Segoe UI',12)).pack(side='left',padx=6)
    tk.Button(controls,text='ПАУЗА / ПУСК',command=lambda:current.update(play=not current['play']),font=('Segoe UI',12)).pack(side='left',padx=6)
    def update():
        if current['play']:current['seconds']=min(30,current['seconds']+0.2)
        photo=ImageTk.PhotoImage(render(current['case'],current['seconds'],current['compare']))
        view.configure(image=photo);view.image=photo
        root.after(50,update)
    update();root.mainloop()


if __name__=='__main__':main()
