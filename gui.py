try:
    from tkinter import *
except:
    from Tkinter import *
import time

class GUI:
    def __init__(self, table):
        self.table = table
        self.position_changed = False
        self.refpoints_changed = True
        self.root = Tk()

        button_west = Button(width=10, height=3)
        button_west.grid(row=1, column=0, padx=(10,0))
        button_west["text"] = "left"
        button_west.bind("<ButtonPress>",   lambda x: self._btnpress_direction("left"))
        button_west.bind("<ButtonRelease>", lambda x: self._btnrelease_direction("left"))

        button_east = Button(width=10, height=3)
        button_east.grid(row=1, column=2, padx=(0,10))
        button_east["text"] = "right"
        button_east.bind("<ButtonPress>",   lambda x: self._btnpress_direction("right"))
        button_east.bind("<ButtonRelease>", lambda x: self._btnrelease_direction("right"))

        button_north = Button(width=10, height=3)
        button_north.grid(row=0, column=1, pady=(10,5))
        button_north["text"] = "forward"
        button_north.bind("<ButtonPress>",   lambda x: self._btnpress_direction("forward"))
        button_north.bind("<ButtonRelease>", lambda x: self._btnrelease_direction("forward"))

        button_south = Button(width=10, height=3)
        button_south.grid(row=2, column=1, pady=(5,10))
        button_south["text"] = "backward"
        button_south.bind("<ButtonPress>",   lambda x: self._btnpress_direction("backward"))
        button_south.bind("<ButtonRelease>", lambda x: self._btnrelease_direction("backward"))

        button_up = Button(width=10, height=3)
        button_up.grid(row=0, rowspan=2, column=3, padx=20, pady=20)
        button_up["text"] = "up"
        button_up.bind("<ButtonPress>",   lambda x: self._btnpress_direction("up"))
        button_up.bind("<ButtonRelease>", lambda x: self._btnrelease_direction("up"))

        button_down = Button(width=10, height=3)
        button_down.grid(row=1, rowspan=2, column=3, padx=20, pady=20)
        button_down["text"] = "down"
        button_down.bind("<ButtonPress>",   lambda x: self._btnpress_direction("down"))
        button_down.bind("<ButtonRelease>", lambda x: self._btnrelease_direction("down"))


        self.position_label = Label()
        self.position_label["text"] = str(table.get_position())
        self.position_label.grid(row=3, columnspan=3, ipadx=20, ipady=20)

        button_set_zero = Button(width=20)
        button_set_zero.grid(row=4, columnspan=2, padx=15, pady=(3,0))
        button_set_zero["text"] = "Set this point as NW corner"
        button_set_zero["command"] = self._cmd_origin

        button_set_xpoint = Button(width=20)
        button_set_xpoint.grid(row=5, columnspan=2, padx=15, pady=(3,0))
        button_set_xpoint["text"] = "Set this point as NE corner"
        button_set_xpoint["command"] = self._cmd_xpoint

        button_set_ypoint = Button(width=20)
        button_set_ypoint.grid(row=6, columnspan=2, padx=15, pady=(3,10))
        button_set_ypoint["text"] = "Set this point as SE corner"
        button_set_ypoint["command"] = self._cmd_ypoint

        self.label_origin = Label()
        self.label_origin.grid(row=4, column=2, columnspan=2, sticky="W", ipadx=15)

        self.label_xpoint = Label()
        self.label_xpoint.grid(row=5, column=2, columnspan=2, sticky="W", ipadx=15)

        self.label_ypoint = Label()
        self.label_ypoint.grid(row=6, column=2, columnspan=2, sticky="W", ipadx=15)

        self.update_labels()


    def update_labels(self):
        if self.refpoints_changed:
            self.label_origin["text"] = "origin: " + str(self.table.origin)
            self.label_xpoint["text"] = "xpoint: " + str(self.table.xpoint)
            self.label_ypoint["text"] = "ypoint: " + str(self.table.ypoint)
            self.refpoints_changed = False

        if self.position_changed:
            self.position_label["text"] = str(self.table.get_position())
            self.root.after(10, self.update_labels)

    def _btnpress_direction(self, direction):
        self.table.move(direction)
        self.position_changed = True
        self.root.after(10, self.update_labels)

    def _btnrelease_direction(self, direction):
        self.table.stop(direction)
        time.sleep(0.05)
        self.update_labels()
        self.position_changed = False

    def _cmd_origin(self):
        self.table.set_origin()
        self.refpoints_changed = True
        self.update_labels()

    def _cmd_xpoint(self):
        self.table.set_xpoint()
        self.refpoints_changed = True
        self.update_labels()

    def _cmd_ypoint(self):
        self.table.set_ypoint()
        self.refpoints_changed = True
        self.update_labels()

    def start(self):
        self.root.mainloop()

    def stop(self):
        self.root.destroy()
