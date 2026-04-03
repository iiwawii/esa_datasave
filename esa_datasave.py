import pyvisa
import csv
import tkinter as tk
from tkinter import messagebox


def execute():
    filename = filename_entry.get()
    address = address_entry.get()
    visa_address_esa='GPIB0::18::INSTR'
    rm = pyvisa.ResourceManager()
    esa=rm.open_resource(visa_address_esa)
    esa.timeout=20000
    print(esa.query('*IDN?'))
    print('1')
    esa.write(f":MMEM:STOR:TRAC TRACE1,'C:\{filename}.csv'")
    print('2')
    data = esa.query(f":MMEMory:DATA? 'C:\{filename}.csv'")
    data = data.split('\n')
    with open(f'{address}\{filename}.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(row.split(',') for row in data)

    # print(esa.query(':MMEM:STOR:SCR "A:myscreen.gif"'))
    # print(esa.query(':MMEMory:DATA? '))


    esa.close()
    rm.close()
    
    print('保存成功')
    messagebox.showinfo("执行结果", f"文件{filename}.csv保存成功")




window = tk.Tk()
window.geometry('300x300')
# 设置窗口标题
window.title("E4407B频谱仪数据保存")

# 创建地址输入框
address_label = tk.Label(window, text="输入文件保存地址:")
address_label.pack()

address_entry = tk.Entry(window)
address_entry.pack()

# 创建文件名输入框
filename_label = tk.Label(window, text="保存文件名:")
filename_label.pack()

filename_entry = tk.Entry(window)
filename_entry.pack()


# 创建执行按钮
execute_button = tk.Button(window, text="执行", command=execute)
execute_button.pack()

# 启动主循环
window.mainloop()