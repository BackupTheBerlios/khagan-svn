#!/usr/bin/python

import pygtk
pygtk.require('2.0')
import gtk
import gtk.glade
import phat
import osc
import xml.dom.minidom
import xml.dom.ext

class Khagan:
    ui = '''
    <ui>
    <menubar name="TopBar">
	<menu action="File">
	    <menuitem action="Open"/>
	    <menuitem action="Save"/>
	    <menuitem action="Configure input"/>
	    <menuitem action="Quit"/>
	</menu>
    </menubar>
    <popup name="popup">
	<menuitem name="Split vertical" action="vsplit"/>
	<menuitem name="Split horizontal" action="hsplit"/>
	<menu name="Add widget" action="add">
	    <menuitem name="Add fanslider" action="add_fan"/>
	    <menuitem name="Add knob" action="add_knob"/>
	    <menuitem name="Add sliderbutton" action="add_slider"/>
	    <menuitem name="Add pad" action="add_pad"/>
	</menu>
    </popup>
    <popup name="editPopup">
	<menuitem name="Edit properties" action="edit"/>
	<menuitem name="Delete" action="delete"/>
    </popup>
    </ui>'''
      
    def __init__(self):
        # Create the toplevel window
	window = gtk.Window()
	self.window = window
        window.connect('destroy', lambda w: gtk.main_quit())
        window.set_size_request(300, 300)
        vbox = gtk.VBox()
        window.add(vbox)

        # Create a UIManager instance
        uimanager = gtk.UIManager()

        # Add the accelerator group to the toplevel window
        accelgroup = uimanager.get_accel_group()
        window.add_accel_group(accelgroup)

        # Create an ActionGroup
        topgroup = gtk.ActionGroup('topbar')
        self.topgroup = topgroup
	popupgroup = gtk.ActionGroup('popup')
        self.popupgroup = popupgroup
	editgroup = gtk.ActionGroup('edit')
        self.editgroup = editgroup


        # Create actions
        topgroup.add_actions([('Quit', gtk.STOCK_QUIT, '_Quit me!', None, 'Quit the Program', self.quit_cb), 
				('File', None, '_File'),
				('Save', gtk.STOCK_SAVE, None, None, 'Save current setup', self.save_cb),
				('Configure input', gtk.STOCK_PREFERENCES, 'Configure input', None, 'Save current setup', self.inputd_cb),
				('Open', gtk.STOCK_OPEN, None, None, 'Open setup', self.open_cb)])
								
	popupgroup.add_actions([('vsplit', None, 'Split _vertical', '<Control>v', None, self.vsplit_cb),
				('hsplit', None, 'Split _horizontal', '<Control>h', None, self.hsplit_cb),
				('add', None, '_Add'),
				('add_fan', None, 'Add _fanslider', '<Control>f', None, self.add_fan_cb),
				('add_knob', None, 'Add _knob', '<Control>k', None, self.add_knob_cb),
				('add_slider', None, 'Add _sliderbutton', '<Control>s', None, self.add_slider_cb),
				('add_pad', None, 'Add _pad', '<Control>p', None, self.add_pad_cb)])

	editgroup.add_actions([('edit', gtk.STOCK_PROPERTIES, '_Edit Properties!', '<Control>e', None, self.edit_cb), 
				('delete', gtk.STOCK_DELETE, None, None, None, self.delete_cb)])

       
        # Add the actiongroup to the uimanager
        uimanager.insert_action_group(topgroup, 0)
	uimanager.insert_action_group(popupgroup, 1)
	uimanager.insert_action_group(editgroup, 2)

        # Add a UI description
        uimanager.add_ui_from_string(self.ui)

        # Create a MenuBar
        menubar = uimanager.get_widget('/TopBar')
        vbox.pack_start(menubar, False)

	popup = uimanager.get_widget('/popup')
	self.popup = popup #FIXME

	edit_popup = uimanager.get_widget('/editPopup')
	self.edit_popup = edit_popup #FIXME

	#load glade file for dialogs
	gtk.glade.set_custom_handler(self.glade_custom_handler)
	#self.gladexml = gtk.glade.XML("khagan.glade")

	#create initial placeholder
	frame = gtk.Frame()
	frame.set_shadow_type(gtk.SHADOW_NONE)
	button = gtk.Button()
	button.set_relief(gtk.RELIEF_HALF)
	button.connect('button_press_event', self.popup_cb)
	self.cur_widget = button
	frame.add(button)
        vbox.pack_start(frame)

        window.show_all()
        return

    def quit_cb(self, b):
        print 'Quitting program'
        gtk.main_quit()

    def inputd_cb(self, b):
	inputd = gtk.InputDialog()
        inputd.connect("destroy", lambda w: inputd.destroy())
	inputd.show()
	inputd.run()
	inputd.destroy()
	return
        

    def save_cb(self, b):
	print 'Saving'
	doc = xml.dom.minidom.Document()
	parent_node = doc.appendChild(doc.createElement("gui"))
	for child in self.window.get_children():
	    self.save_rec(doc, parent_node, child)
	dialog = gtk.FileChooserDialog('Save as', self.window, gtk.FILE_CHOOSER_ACTION_SAVE, buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_SAVE,gtk.RESPONSE_OK))
	if dialog.run() == gtk.RESPONSE_OK:
	    outfile = file(dialog.get_filename(), 'w')
	    #xml.dom.ext.PrettyPrint(doc)
	    xml.dom.ext.PrettyPrint(doc, outfile)
	dialog.destroy()
	return

    def save_rec(self, doc, parent_node, child):	
	#if it's anything that has params just print it
	widget_node = None
	if(type(child) == phat.HFanSlider) or (type(child) == phat.SliderButton):
	    self.save_widget(child, doc, parent_node)
	elif type(child) == phat.Pad:
	    self.save_widget_pad(child, doc, parent_node)
	elif(type(child) == gtk.Button):
	    widget_node = doc.createElement('widget')
	    parent_node.appendChild(widget_node)
	    node = doc.createElement('name')
	    widget_node.appendChild(node)
	    node.appendChild(doc.createTextNode(child.get_name()))
	#if it's here it's a container widget, so recurse
	else:
	    if(type(child) == gtk.HBox):
		widget_node = doc.createElement('vsplit')
		parent_node.appendChild(widget_node)
	    elif(type(child) == gtk.VBox):
		widget_node = doc.createElement('hsplit')
		parent_node.appendChild(widget_node)
	    
	    if issubclass(type(child), gtk.Container):
		for child2 in child.get_children():
		    if(widget_node):
			self.save_rec(doc, widget_node, child2)	
		    else:
			self.save_rec(doc, parent_node, child2)
		
	return

    def save_widget(self, child, doc, parent_node):
	widget_node = doc.createElement('widget')
	parent_node.appendChild(widget_node)
	names = ['name', 'value', 'min', 'max', 'osc_path', 'port']
	values = [child.get_name(), str(child.get_value()), str(child.get_adjustment().lower), str(child.get_adjustment().upper), child.osc_path[0], str(child.port[0])]
	
	for i in range(len(names)):
	    node = doc.createElement(names[i])
	    widget_node.appendChild(node)
	    node.appendChild(doc.createTextNode(values[i]))
	return
    

    def save_widget_pad(self, child, doc, parent_node):
	widget_node = doc.createElement('widget')
	parent_node.appendChild(widget_node)

	node = doc.createElement('name')
	widget_node.appendChild(node)
	node.appendChild(doc.createTextNode(child.get_name()))

	for i in range(5):
	    node = doc.createElement('osc_path'+str(i))
	    widget_node.appendChild(node)
	    node.appendChild(doc.createTextNode(child.osc_path[i]))

	for i in range(5):
	    node = doc.createElement('port'+str(i))
	    widget_node.appendChild(node)
	    node.appendChild(doc.createTextNode(child.port[i]))
	return	


    def open_cb(self, b):
	print 'Opening'
	doc = xml.dom.minidom.Document()	
	dialog = gtk.FileChooserDialog('Open', self.window, gtk.FILE_CHOOSER_ACTION_OPEN, buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
	if dialog.run() == gtk.RESPONSE_OK:
	    doc = xml.dom.minidom.parse(dialog.get_filename())
	    #xml.dom.ext.PrettyPrint(doc)
	    
	dialog.destroy()
	return

    def popup_cb(self, widget, event):
	self.cur_widget = widget
	self.popup.popup(None, None, None, event.button, event.time)
	return

    def edit_popup_cb(self, widget, event):
	if event.button == 3:
	    self.cur_widget = widget
	    self.edit_popup.popup(None, None, None, event.button, event.time)
	return

    def add_knob_cb(self, b):
	print 'Quitting program'
	return
        #
    def add_slider_cb(self, b):
	print 'adding sliderbutton'
	self.add_widget('add_slider')
	return
        #
    def add_fan_cb(self, b):
	print 'adding fan slider'
	self.add_widget('add_fan')
	return
        #
    def add_pad_cb(self, b):
	print 'adding pad slider'
	self.add_widget('add_pad')
	return

    def edit_cb(self, b):
	if(type(self.cur_widget) == phat.Pad):
	    self.edit_pad(b)
	else:
	    self.edit_continuous(b)

    def edit_continuous(self, b):
	#open the corrent dialog from glade file
	gladexml = gtk.glade.XML("khagan.glade", 'widget_continuous-1')
	dialog = gladexml.get_widget('widget_continuous-1')
	if hasattr(self.cur_widget, 'osc_path'):
	    gladexml.get_widget('entry_path').set_text(self.cur_widget.osc_path[0])
	if hasattr(self.cur_widget, 'port'):
	    gladexml.get_widget('entry_port').set_text(str(self.cur_widget.port[0]))
	gladexml.get_widget('custom3').set_value(self.cur_widget.get_adjustment().lower)
	gladexml.get_widget('custom2').set_value(self.cur_widget.get_adjustment().upper)
	gladexml.get_widget('button1').connect("clicked", lambda w: dialog.destroy())
	gladexml.get_widget('button2').connect("clicked", self.edit_okay_cb, gladexml)
	dialog.show_all()
	return

    def edit_pad(self, b):
	#open the corrent dialog from glade file
	gladexml = gtk.glade.XML("khagan.glade", 'widget_pad_tablet')
	dialog = gladexml.get_widget('widget_pad_tablet')
	#entries in list
	entry = ['entry_path_h', 'entry_path_v', 'entry_path_ht', 'entry_path_vt', 'entry_path_p']
	ports = ['entry_port_h', 'entry_port_v', 'entry_port_ht', 'entry_port_vt', 'entry_port_p']
	if hasattr(self.cur_widget, 'osc_path'):
	    for i in range(len(entry)):
	    		gladexml.get_widget(entry[i]).set_text(self.cur_widget.osc_path[i])
	if hasattr(self.cur_widget, 'port'):
	    for i in range(len(ports)):
	    		gladexml.get_widget(entry[i]).set_text(str(self.cur_widget.port[i]))
		
	#gladexml.get_widget('custom3').set_value(self.cur_widget.get_adjustment().lower)
	#gladexml.get_widget('custom2').set_value(self.cur_widget.get_adjustment().upper)
	gladexml.get_widget('button_cancel').connect("clicked", lambda w: dialog.destroy())
	gladexml.get_widget('button_ok').connect("clicked", self.edit_okay_pad_cb, gladexml)
	dialog.show_all()
	return


    def edit_okay_cb(self, button, gladexml):
	#if they clicked okay, change current values.
	self.cur_widget.port = [0]
	self.cur_widget.osc_path = [0]
	self.cur_widget.split_path = [0]
	self.cur_widget.sub_index = [0]
	self.split_path(self.cur_widget, gladexml.get_widget('entry_path').get_text(), 0)
	self.cur_widget.port[0] = int(gladexml.get_widget('entry_port').get_text())
	self.cur_widget.set_range(gladexml.get_widget('custom3').get_value(), gladexml.get_widget('custom2').get_value())
	gladexml.get_widget('widget_continuous-1').destroy()
	return
    
    def edit_okay_pad_cb(self, button, gladexml):
	#if they clicked okay, change current values.
	entry = ['entry_path_h', 'entry_path_v', 'entry_path_ht', 'entry_path_vt', 'entry_path_p']
	port_list = ['entry_port_h', 'entry_port_v', 'entry_port_ht', 'entry_port_vt', 'entry_port_p']
	#init port, osc_path, split_path
	self.cur_widget.port = range(5)
	self.cur_widget.osc_path = range(5)
	self.cur_widget.split_path = range(5)
	self.cur_widget.sub_index = range(5)
	for i in range(len(entry)):
	    self.split_path(self.cur_widget, gladexml.get_widget(entry[i]).get_text(), i)
	    self.cur_widget.port[i] = int(gladexml.get_widget(port_list[i]).get_text())
	#self.cur_widget.set_range(gladexml.get_widget('custom3').get_value(), gladexml.get_widget('custom2').get_value())
	gladexml.get_widget('widget_pad_tablet').destroy()
	return

    def split_path(self, widget, path, num):
	widget.osc_path[num] = path
	widget.split_path[num] = path.split(' ')
	i = -1 # list index from zero
	for item in widget.split_path[num]:
	    i+=1
	    if item.isdigit():
		widget.split_path[num][i] = int(item)
	    if item == '%':
		widget.sub_index[num] = i
	return

    def osc_send_cb(self,widget):
	#osc.Message("/filter/cutoff", [145.1232]).sendlocal(port)
	#sub in current widget value to sub location. Iterate over all paths for multid widgets
	if hasattr(widget, 'split_path'):
	    if(type(widget) == phat.Pad):
		parms = [widget.get_x(), widget.get_y(), widget.get_xtilt(), widget.get_ytilt(), widget.get_pressure()]
		print parms
		for i in range(len(widget.split_path)):
		    widget.split_path[i][widget.sub_index[i]] = parms[i]
		    osc.Message(widget.split_path[i][0], widget.split_path[i][1:len(widget.split_path)]).sendlocal(widget.port[i])
		    #print 'osc.Message(', widget.split_path[i][0], widget.split_path[i][1:len(widget.split_path)], ').sendlocal(', widget.port[i],')'
	    else:
		osc.Message(widget.split_path[0][0], widget.split_path[0][1:len(widget.split_path)]).sendlocal(widget.port[0])
	    #print 'osc.Message(', widget.split_path[0], widget.split_path[1:len(widget.split_path)], ').sendlocal(', widget.port, ')'
	return
	

    def delete_cb(self, b):
	#remove current widget
	parentframe = self.cur_widget.get_parent()
	parentframe.remove(self.cur_widget)
	#and add the placeholder
	button = gtk.Button()
	button.connect('button_press_event', self.popup_cb)
	button.set_relief(gtk.RELIEF_HALF)
	parentframe.add(button)
	parentframe.show_all()
	return

    def add_widget(self, type):
	parentframe = self.cur_widget.get_parent()
	parentframe.remove(self.cur_widget)
	
	if type == 'add_fan':
	    widget = phat.phat_hfan_slider_new_with_range(1.0, 0.0, 200000.0, 0.1)
	elif type == 'add_slider':
	    widget = phat.phat_slider_button_new_with_range(1.0, 0.0, 200000.0, 0.1, 2)
	elif type == 'add_pad':
	    widget = phat.Pad()

	
	widget.connect('value-changed', self.osc_send_cb)
	widget.connect('button_press_event', self.edit_popup_cb)
	parentframe.add(widget)
	parentframe.show_all()	
	

    #split the current cell vertical by creating a hbox. Everything goes in a frame first
    def vsplit_cb(self, b):
	#creat a new hbox where the widget was and add the 2 buttons to it. 
	self.split('v')
        return
    
    def hsplit_cb(self, b):
	#creat a new vbox where the widget was and add the 2 buttons to it. 
	self.split('h')
	return

    
    def glade_custom_handler (self, glade, func_name, name, str1, str2, int1, int2):
        if func_name == 'PhatSliderButton':
	    temp = phat.phat_slider_button_new_with_range(1.0, 0.0, 2.0, 0.1, 2)
	    temp.show_all()
	return temp
	
    
    def split(self, dir):
	if(dir == 'v'):
	    box = gtk.HBox(True)
	else:
	    box = gtk.VBox(True)
	
	frame1 = gtk.Frame()
	frame1.set_shadow_type(gtk.SHADOW_NONE)
	button1 = gtk.Button()
	button1.connect('button_press_event', self.popup_cb)
	button1.set_relief(gtk.RELIEF_HALF)
	frame1.add(button1)
        box.pack_start(frame1)
	button2 = gtk.Button()
	frame2 = gtk.Frame()
	frame2.set_shadow_type(gtk.SHADOW_NONE)
	button2.connect('button_press_event', self.popup_cb)
	button2.set_relief(gtk.RELIEF_HALF)
	frame2.add(button2)
        box.pack_start(frame2)	
	#add the new box to the parent of placeholder
	parentframe = self.cur_widget.get_parent()
	parentframe.remove(self.cur_widget)
	parentframe.add(box)
	#and removet he place holder
	parentframe.show_all()

	

if __name__ == '__main__':
    ba = Khagan()
    gtk.main()
