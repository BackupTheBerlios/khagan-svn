#!/usr/bin/python

import pygtk
pygtk.require('2.0')
import gtk
import gtk.glade
import phat
import osc
import os.path
import xml.dom.minidom
import xml.dom.ext
import getopt, sys
import khagan_globals as pglobals

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
	<menu action="Help">
	    <menuitem action="About"/>
	</menu>
    </menubar>
    <popup name="popup">
	<menuitem name="Split vertical" action="vsplit"/>
	<menuitem name="Split horizontal" action="hsplit"/>
	<menuitem name="Join" action="join"/>
	<menuitem name="Import" action="import"/>
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
	gtk.window_set_default_icon_from_file(pglobals.data_dir+"/pixmaps/khagan_icon_24px.png")
	window = gtk.Window()
	self.window = window
	window.set_title("Khagan")
        window.connect('destroy', lambda w: gtk.main_quit())
        window.set_size_request(300, 300)
        vbox = gtk.VBox()
	window.add(vbox)

        # Create a UIManager instance
        uimanager = gtk.UIManager()
	self.uimanager = uimanager

        # Add the accelerator group to the toplevel window
        accelgroup = uimanager.get_accel_group()
        window.add_accel_group(accelgroup)

        # Create an ActionGroup
        topgroup = gtk.ActionGroup('topbar')
        self.topgroup = topgroup


        # Create actions
        topgroup.add_actions([('Quit', gtk.STOCK_QUIT, None, None, 'Quit the Program', self.quit_cb), 
				('File', None, '_File'),
				('Save', gtk.STOCK_SAVE, None, None, 'Save current setup', self.save_cb),
				('Configure input', gtk.STOCK_PREFERENCES, 'Configure input', None, 'Save current setup', self.inputd_cb),
				('Open', gtk.STOCK_OPEN, None, None, 'Open setup', self.open_cb),
				('Help', None, '_Help'),
				('About', gtk.STOCK_ABOUT, None, None, 'About', self.about_cb)])

	# these 2 are just here as place holders so it doesn't worry about missing actions on initing the topbar
	popupgroup = gtk.ActionGroup('popup')
	self.tempgroup1 = popupgroup
       	popupgroup.add_actions([('vsplit', None, 'Split _vertical'),
				('hsplit', None, 'Split _horizontal'),
				('join', None, '_Join cells'),
				('add', None, '_Add'),
				('add_fan', None, '_fanslider'),
				('add_knob', None, '_knob'),
				('add_slider', None, '_sliderbutton'),
				('add_pad', None, '_pad'),
				('import', None, '_import')
				])

	editgroup = gtk.ActionGroup('edit')
	editgroup.add_actions([('edit', gtk.STOCK_PROPERTIES, '_Edit Properties'), 
				('delete', gtk.STOCK_DELETE, None)])	    
	self.tempgroup2 = editgroup
	uimanager.insert_action_group(popupgroup, 1)
	uimanager.insert_action_group(editgroup, 1)						

       
        # Add the actiongroup to the uimanager
        uimanager.insert_action_group(topgroup, 0)

        # Add a UI description
        uimanager.add_ui_from_string(self.ui)

        # Create a MenuBar
        menubar = uimanager.get_widget('/TopBar')
        vbox.pack_start(menubar, False)

	#load glade file for dialogs
	gtk.glade.set_custom_handler(self.glade_custom_handler)
	#self.gladexml = gtk.glade.XML(pglobals.data_dir+"/khagan.glade")

	#create initial placeholder
	frame = gtk.Frame()
	# use that frame as base for ui
	self.topframe = frame
	frame.set_shadow_type(gtk.SHADOW_NONE)
	button = gtk.Button()
	button.set_relief(gtk.RELIEF_HALF)
	button.connect('button_press_event', self.popup_cb)
	frame.add(button)
        vbox.pack_start(frame)

	#restore setting for xinput devices
	self.restore_devices()

        window.show_all()
        return

    def quit_cb(self, b):
        #print 'Quitting program'
        gtk.main_quit()

    #restore setting for xinput devices
    def restore_devices(self):
	#check if file exists with try
	try:
	    infile = file(os.path.expanduser('~/.khagan/khdevice.conf'), 'r')
        except IOError:
            return
	for line in infile.readlines():
	    elements = line.split(',')
	    for device in gtk.gdk.devices_list():
		if device.name == elements[0]:
		    #print "device name is ", device.name
		    #set the mode for the device after creating the enum for that mode, wacky stuff.
		    device.set_mode(gtk.gdk.InputMode(int(elements[1])))
	    infile.close()
	return	
	

    def inputd_cb(self, b):
	inputd = gtk.InputDialog()
        inputd.connect("destroy", lambda w: inputd.destroy())
	inputd.action_area.get_children()[1].connect('button_press_event', lambda w, x: inputd.destroy())
	inputd.show()
	inputd.run()
	inputd.destroy()
	return

    def about_cb(self, b):
	gladexml = gtk.glade.XML(pglobals.data_dir+"/khagan.glade", 'about_dialog')
	dialog = gladexml.get_widget('about_dialog')
	dialog.connect("destroy", lambda w: dialog.destroy())
	return        

    def save_cb(self, b):
	#print 'Saving'
	doc = xml.dom.minidom.Document()
	parent_node = doc.appendChild(doc.createElement("gui"))
	for child in self.window.get_children():
	    self.save_rec(doc, parent_node, child)
	dialog = gtk.FileChooserDialog('Save as', self.window, gtk.FILE_CHOOSER_ACTION_SAVE, buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_SAVE,gtk.RESPONSE_OK))
	if dialog.run() == gtk.RESPONSE_OK:
	    outfile = file(dialog.get_filename(), 'w')
	    xml.dom.ext.Print(doc, outfile)
	    #xml.dom.ext.PrettyPrint(doc, outfile)
	dialog.destroy()
	return

    def save_rec(self, doc, parent_node, child):	
	#if it's anything that has params just print it
	widget_node = None
	if(type(child) == phat.HFanSlider) or (type(child) == phat.SliderButton) or (type(child) == phat.Knob):
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
		#first vbox is actually from the window, so don't save it.
		if type(child.get_parent()) != gtk.Window:		    
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
	if (type(child) == phat.SliderButton):
	    names = ['name', 'value', 'min', 'max', 'osc_path', 'port', 'label']
	    values = [child.get_name(), str(child.get_value()), str(child.get_adjustment().lower), str(child.get_adjustment().upper), child.osc_path[0], str(child.port[0]), child.label.get_text()]	
	else:
	    names = ['name', 'value', 'min', 'max', 'osc_path', 'port', 'label', 'is_log']
	    values = [child.get_name(), str(child.get_value()), str(child.get_adjustment().lower), str(child.get_adjustment().upper), child.osc_path[0], str(child.port[0]), child.label.get_text(), str(child.is_log())]
	
	for i in range(len(names)):
	    node = doc.createElement(names[i])
	    widget_node.appendChild(node)
	    node.appendChild(doc.createTextNode(values[i]))
	return
    

    def save_widget_pad(self, child, doc, parent_node):
	is_logs = [child.x_is_log(), child.y_is_log(), child.xtilt_is_log(), child.ytilt_is_log(), child.pressure_is_log()]
	min_vals = [child.get_x().lower, child.get_y().lower, child.get_xtilt().lower, child.get_ytilt().lower, child.get_pressure().lower]
	max_vals = [child.get_x().upper, child.get_y().upper, child.get_xtilt().upper, child.get_ytilt().upper, child.get_pressure().upper]

	widget_node = doc.createElement('widget')
	parent_node.appendChild(widget_node)

	node = doc.createElement('name')
	widget_node.appendChild(node)
	node.appendChild(doc.createTextNode(child.get_name()))

	node = doc.createElement('label')
	widget_node.appendChild(node)
	node.appendChild(doc.createTextNode(child.label.get_text()))

	for i in range(5):
	    node = doc.createElement('osc_path')
	    widget_node.appendChild(node)
	    node.appendChild(doc.createTextNode(child.osc_path[i]))

	for i in range(5):
	    node = doc.createElement('port')
	    widget_node.appendChild(node)
	    node.appendChild(doc.createTextNode(str(child.port[i])))
	
	for i in range(len(is_logs)):
	    node = doc.createElement('is_log')
	    widget_node.appendChild(node)
	    node.appendChild(doc.createTextNode(str(is_logs[i])))

	for i in range(len(min_vals)):
	    node = doc.createElement('min')
	    widget_node.appendChild(node)
	    node.appendChild(doc.createTextNode(str(min_vals[i])))
	for i in range(len(min_vals)):
	    node = doc.createElement('max')
	    widget_node.appendChild(node)
	    node.appendChild(doc.createTextNode(str(max_vals[i])))

	return	


    def open_cb(self, b):
	#print 'Opening'
	doc = xml.dom.minidom.Document()	
	dialog = gtk.FileChooserDialog('Open', self.window, gtk.FILE_CHOOSER_ACTION_OPEN, buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
	if dialog.run() == gtk.RESPONSE_OK:
	    doc = xml.dom.minidom.parse(dialog.get_filename())
	    parent_node = doc.getElementsByTagName('gui')
	    # destroy current ui first
	    for child in self.topframe.get_children():
		child.destroy()

	    for child in parent_node[0].childNodes:
		self.open_rec(child, self.topframe)
	    self.topframe.show_all()		
	    #for node in self.doc_order_iter(doc):
		#print node
	dialog.destroy()
	return

    def open_file(self, filename):
	#print 'Opening'
	doc = xml.dom.minidom.Document()	
	doc = xml.dom.minidom.parse(filename)
	parent_node = doc.getElementsByTagName('gui')
	# destroy current ui first
	for child in self.topframe.get_children():
	    child.destroy()

	for child in parent_node[0].childNodes:
	    self.open_rec(child, self.topframe)
	self.topframe.show_all()		
	#for node in self.doc_order_iter(doc):
	#print node
	return

    def import_cb(self, b, widget):
	#print 'Importing'
	doc = xml.dom.minidom.Document()	
	dialog = gtk.FileChooserDialog('Import', self.window, gtk.FILE_CHOOSER_ACTION_OPEN, buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
	if dialog.run() == gtk.RESPONSE_OK:
	    parentframe = widget.get_parent()
	    parentframe.remove(widget)
	    doc = xml.dom.minidom.parse(dialog.get_filename())
	    parent_node = doc.getElementsByTagName('gui')
	    for child in parent_node[0].childNodes:
		self.open_rec(child, parentframe)
	    widget.show_all()		
	    #for node in self.doc_order_iter(doc):
		#print node
	dialog.destroy()
	return


    def open_rec(self, node, parent_widget):
	#if it's a grouping element
	if node.nodeName == 'hsplit' or node.nodeName == 'vsplit':
	    if node.nodeName == 'vsplit':
		box = gtk.HBox(True)
	    if node.nodeName == 'hsplit':
		box = gtk.VBox(True)
	    frame1 = gtk.Frame()
	    frame1.set_shadow_type(gtk.SHADOW_NONE)
	    box.pack_start(frame1)
	    frame2 = gtk.Frame()
	    frame2.set_shadow_type(gtk.SHADOW_NONE)
	    box.pack_start(frame2)	
	    #add the new box to the parent of placeholder
	    parent_widget.add(box)
	    #and removet he place holder
	    parent_widget.show_all()
	    #recure left
	    self.open_rec(node.childNodes[0], frame1)
	    #recure right
	    self.open_rec(node.childNodes[1], frame2)
	#otherwise it's a widget, but don't use an else because anything else could be in here.
	if node.nodeName == 'widget':
	    name = node.getElementsByTagName('name')[0].firstChild.data
	    if name == 'GtkButton':
		button1 = gtk.Button()
		button1.connect('button_press_event', self.popup_cb)
		button1.set_relief(gtk.RELIEF_HALF)
		parent_widget.add(button1)
		parent_widget.show_all()
		return
	    elif name == 'PhatHFanSlider':
		widget = phat.phat_hfan_slider_new_with_range(float(node.getElementsByTagName('value')[0].firstChild.data), float(node.getElementsByTagName('min')[0].firstChild.data), float(node.getElementsByTagName('max')[0].firstChild.data), 0.1)
		widget.port = [0]
		widget.osc_path = [0]
		widget.split_path = [0]
		widget.sub_index = [0]
		self.split_path(widget, node.getElementsByTagName('osc_path')[0].firstChild.data, 0)
		widget.port[0] = int(node.getElementsByTagName('port')[0].firstChild.data)
		widget.label = gtk.Label(node.getElementsByTagName('label')[0].firstChild.data)
		parent_widget.set_label_widget(widget.label)
		widget.set_log(interpret_bool(node.getElementsByTagName('is_log')[0].firstChild.data))
		widget.set_value(float(node.getElementsByTagName('value')[0].firstChild.data)) 
	    elif name == 'PhatSliderButton':
		widget = phat.phat_slider_button_new_with_range(float(node.getElementsByTagName('value')[0].firstChild.data), float(node.getElementsByTagName('min')[0].firstChild.data), float(node.getElementsByTagName('max')[0].firstChild.data), 0.1, 2)
		widget.port = [0]
		widget.osc_path = [0]
		widget.split_path = [0]
		widget.sub_index = [0]
		self.split_path(widget, node.getElementsByTagName('osc_path')[0].firstChild.data, 0)
		widget.port[0] = int(node.getElementsByTagName('port')[0].firstChild.data)
		widget.label = gtk.Label(node.getElementsByTagName('label')[0].firstChild.data)
		parent_widget.set_label_widget(widget.label)
		widget.set_value(float(node.getElementsByTagName('value')[0].firstChild.data))
	    elif name == 'PhatKnob':
		widget = phat.phat_knob_new_with_range(float(node.getElementsByTagName('value')[0].firstChild.data), float(node.getElementsByTagName('min')[0].firstChild.data), float(node.getElementsByTagName('max')[0].firstChild.data), 0.1)
		widget.port = [0]
		widget.osc_path = [0]
		widget.split_path = [0]
		widget.sub_index = [0]
		self.split_path(widget, node.getElementsByTagName('osc_path')[0].firstChild.data, 0)
		widget.port[0] = int(node.getElementsByTagName('port')[0].firstChild.data)
		widget.label = gtk.Label(node.getElementsByTagName('label')[0].firstChild.data)
		widget.set_log(interpret_bool(node.getElementsByTagName('is_log')[0].firstChild.data))
		parent_widget.set_label_widget(widget.label)
		widget.set_value(float(node.getElementsByTagName('value')[0].firstChild.data)) 
	    elif name == 'PhatPad':
		widget = phat.Pad()
		widget.port = range(5)
		widget.osc_path = range(5)
		widget.split_path = range(5)
		widget.sub_index = range(5)
		widget.label = gtk.Label(node.getElementsByTagName('label')[0].firstChild.data)
		parent_widget.set_label_widget(widget.label)
		radio_setters = [widget.set_x_log, widget.set_y_log, widget.set_xtilt_log, widget.set_ytilt_log, widget.set_pressure_log]
		adjusts = [widget.get_x(), widget.get_y(), widget.get_xtilt(), widget.get_ytilt(), widget.get_pressure()]

		
		i = 0
		for child in node.getElementsByTagName('osc_path'):
		    if(child.firstChild != None):
			self.split_path(widget, child.firstChild.data, i)
			#print 'in osc path',  child.firstChild.data
		    else:
			self.split_path(widget, '', i)
		    i+=1
		i = 0
		for child in node.getElementsByTagName('port'):
		    if(child.firstChild != None):
			widget.port[i] = int(child.firstChild.data)
			#print 'in port',  child.firstChild.data
		    else:
			widget.port[i] = 0
		    i+=1
		i = 0
		for child in node.getElementsByTagName('is_log'):
		    if(child.firstChild != None):
			apply(radio_setters[i], [interpret_bool(child.firstChild.data)]) 
		    i+=1
		i = 0
		for child in node.getElementsByTagName('min'):
		    if(child.firstChild != None):
			setattr(adjusts[i], 'lower', float(child.firstChild.data))
		    i+=1
		i = 0
		for child in node.getElementsByTagName('max'):
		    if(child.firstChild != None):
			setattr(adjusts[i], 'upper', float(child.firstChild.data))
		    i+=1
			
	    widget.connect('value-changed', self.osc_send_cb)
	    widget.connect('button_press_event', self.edit_popup_cb)
	    parent_widget.add(widget)
	    parent_widget.show_all()	    
			
		

    def doc_order_iter(self, node):
	"""
	Iterates over each node in document order,
	returning each in turn
	"""
	#Document order returns the current node,
	#then each of its children in turn
	yield node
	for child in node.childNodes:
	    #Create a generator for each child,
	    #Over which to iterate
	    for cn in self.doc_order_iter(child):
		yield cn
	return

    def popup_cb(self, widget, event):
	self.uimanager.remove_action_group(self.tempgroup1)
	popupgroup = gtk.ActionGroup('popup')
       	popupgroup.add_actions([('vsplit', None, 'Split _vertical', '<Control>v', None, self.vsplit_cb),
				('hsplit', None, 'Split _horizontal', '<Control>h', None, self.hsplit_cb),
				('join', None, '_Join cells', '<Control>j', None, self.join_cb),
				('import', None, '_Import File', '<Control>i', None, self.import_cb),
				('add', None, '_Add'),
				('add_fan', None, '_fanslider', '<Control>f', None, self.add_fan_cb),
				('add_knob', None, '_knob', '<Control>k', None, self.add_knob_cb),
				('add_slider', None, '_sliderbutton', '<Control>s', None, self.add_slider_cb),
				('add_pad', None, '_pad', '<Control>p', None, self.add_pad_cb)], widget)

	self.uimanager.insert_action_group(popupgroup, 1)
	popup = self.uimanager.get_widget('/popup')
	popup.popup(None, None, None, event.button, event.time)
	#sub for removal next time though, otherwise the are inserted and never removed
	self.tempgroup1 = popupgroup
	#self.uimanager.remove_action_group(popupgroup)
	return

    def edit_popup_cb(self, widget, event):
	if event.button == 3:
	    self.uimanager.remove_action_group(self.tempgroup2)
	    editgroup = gtk.ActionGroup('edit')
	    editgroup.add_actions([('edit', gtk.STOCK_PROPERTIES, '_Edit Properties', '<Control>e', None, self.edit_cb), 
				('delete', gtk.STOCK_DELETE, None, None, None, self.delete_cb)], widget)	    
	    
	    self.uimanager.insert_action_group(editgroup, 2)
	    edit_popup = self.uimanager.get_widget('/editPopup')
	    edit_popup.popup(None, None, None, event.button, event.time)
	    #sub for removal next time though
	    self.tempgroup2 = editgroup
	return

    def add_knob_cb(self, b, widget):
	self.add_widget('add_knob', widget)
	return
        #
    def add_slider_cb(self, b, widget):
	#print 'adding sliderbutton'
	self.add_widget('add_slider', widget)
	return
        #
    def add_fan_cb(self, b, widget):
	#print 'adding fan slider'
	self.add_widget('add_fan', widget)
	return
        #
    def add_pad_cb(self, b, widget):
	#print 'adding pad slider'
	self.add_widget('add_pad', widget)
	return

    def edit_cb(self, b, widget):
	if(type(widget) == phat.Pad):
	    self.edit_pad(widget)
	else:
	    self.edit_continuous(widget)

    def edit_continuous(self, widget):
	#open the corrent dialog from glade file
	gladexml = gtk.glade.XML(pglobals.data_dir+"/khagan.glade", 'widget_continuous')
	dialog = gladexml.get_widget('widget_continuous')
	if hasattr(widget, 'osc_path'):
	    if type(widget.osc_path[0]) == str or type(widget.osc_path[0]) == unicode: 
		gladexml.get_widget('entry_path').set_text(widget.osc_path[0])
	if hasattr(widget, 'port'):
	    gladexml.get_widget('entry_port').set_text(str(widget.port[0]))
	if hasattr(widget, 'label'):
	    gladexml.get_widget('entry_label').set_text(str(widget.label.get_text()))
	gladexml.get_widget('sbutton_min').set_value(widget.get_adjustment().lower)
	gladexml.get_widget('sbutton_max').set_value(widget.get_adjustment().upper)
	if(type(widget) != phat.SliderButton):
	    gladexml.get_widget('radio_log').set_active(widget.is_log())
	gladexml.get_widget('button_cancel').connect("clicked", lambda w: dialog.destroy())
	gladexml.get_widget('button_ok').connect("clicked", self.edit_okay_cb, gladexml, widget)
	dialog.show_all()
	return

    def edit_pad(self, widget):
	#open the corrent dialog from glade file
	gladexml = gtk.glade.XML(pglobals.data_dir+"/khagan.glade", 'widget_pad')
	dialog = gladexml.get_widget('widget_pad')
	#entries in list
	entry = ['entry_path_h', 'entry_path_v', 'entry_path_ht', 'entry_path_vt', 'entry_path_p']
	ports = ['entry_port_h', 'entry_port_v', 'entry_port_ht', 'entry_port_vt', 'entry_port_p']
	mins = ['sbutton_min_h', 'sbutton_min_v', 'sbutton_min_ht', 'sbutton_min_vt', 'sbutton_min_p']
	# this looks dodgy, got to be a better way.
	min_vals = [widget.get_x().lower, widget.get_y().lower, widget.get_xtilt().lower, widget.get_ytilt().lower, widget.get_pressure().lower]
	maxs = ['sbutton_max_h', 'sbutton_max_v', 'sbutton_max_ht', 'sbutton_max_vt', 'sbutton_max_p']
	max_vals = [widget.get_x().upper, widget.get_y().upper, widget.get_xtilt().upper, widget.get_ytilt().upper, widget.get_pressure().upper]
	radios = ['radio_log_h', 'radio_log_v', 'radio_log_ht', 'radio_log_vt', 'radio_log_p']
	radio_vals = [widget.x_is_log(), widget.y_is_log(), widget.xtilt_is_log(), widget.ytilt_is_log(), widget.pressure_is_log()]
	
	if hasattr(widget, 'label'):
	    gladexml.get_widget('entry_label').set_text(str(widget.label.get_text()))
	if hasattr(widget, 'osc_path'):
	    for i in range(len(entry)):
		gladexml.get_widget(entry[i]).set_text(widget.osc_path[i])
	if hasattr(widget, 'port'):
	    for i in range(len(ports)):
		gladexml.get_widget(ports[i]).set_text(str(widget.port[i]))
	for i in range(len(mins)):
	    gladexml.get_widget(mins[i]).set_value(min_vals[i])
	for i in range(len(maxs)):
	    gladexml.get_widget(maxs[i]).set_value(max_vals[i])
	for i in range(len(radios)):
	    gladexml.get_widget(radios[i]).set_active(radio_vals[i]) 
	gladexml.get_widget('button_cancel').connect("clicked", lambda w: dialog.destroy())
	gladexml.get_widget('button_ok').connect("clicked", self.edit_okay_pad_cb, gladexml, widget)
	dialog.show_all()
	return

    def edit_okay_cb(self, button, gladexml, widget):
	#if they clicked okay, change current values.
	widget.port = [0]
	widget.osc_path = [0]
	widget.split_path = [0]
	widget.sub_index = [0]
	if len(gladexml.get_widget('entry_path').get_text()) > 1:
	    self.split_path(widget, gladexml.get_widget('entry_path').get_text(), 0)
	if len(gladexml.get_widget('entry_port').get_text()) > 0:
	    widget.port[0] = int(gladexml.get_widget('entry_port').get_text())
	widget.label.set_text(gladexml.get_widget('entry_label').get_text())
	if(type(widget) != phat.SliderButton):
	    widget.set_log(gladexml.get_widget('radio_log').get_active())
	widget.set_range(gladexml.get_widget('sbutton_min').get_value(), gladexml.get_widget('sbutton_max').get_value())
	gladexml.get_widget('widget_continuous').destroy()
	return
    
    def edit_okay_pad_cb(self, button, gladexml, widget):
	#if they clicked okay, change current values.
	entry = ['entry_path_h', 'entry_path_v', 'entry_path_ht', 'entry_path_vt', 'entry_path_p']
	port_list = ['entry_port_h', 'entry_port_v', 'entry_port_ht', 'entry_port_vt', 'entry_port_p']
	mins = ['sbutton_min_h', 'sbutton_min_v', 'sbutton_min_ht', 'sbutton_min_vt', 'sbutton_min_p']
	maxs = ['sbutton_max_h', 'sbutton_max_v', 'sbutton_max_ht', 'sbutton_max_vt', 'sbutton_max_p']
	adjusts = [widget.get_x(), widget.get_y(), widget.get_xtilt(), widget.get_ytilt(), widget.get_pressure()]
	radios = ['radio_log_h', 'radio_log_v', 'radio_log_ht', 'radio_log_vt', 'radio_log_p']
	radio_setters = [widget.set_x_log, widget.set_y_log, widget.set_xtilt_log, widget.set_ytilt_log, widget.set_pressure_log]

	widget.label.set_text(gladexml.get_widget('entry_label').get_text())

	#init port, osc_path, split_path
	widget.port = range(5)
	widget.osc_path = range(5)
	widget.split_path = range(5)
	widget.sub_index = range(5)
	for i in range(len(entry)):
	    self.split_path(widget, gladexml.get_widget(entry[i]).get_text(), i)
	    if(gladexml.get_widget(port_list[i]).get_text()):
		widget.port[i] = int(gladexml.get_widget(port_list[i]).get_text())
	    else: 
		widget.port[i] = 0
	for i in range(len(mins)):
	    setattr(adjusts[i], 'lower', gladexml.get_widget(mins[i]).get_value())
	    #print "lower", gladexml.get_widget(mins[i]).get_value(), "upper", gladexml.get_widget(maxs[i]).get_value()
	    setattr(adjusts[i], 'upper', gladexml.get_widget(maxs[i]).get_value())
	for i in range(len(radios)):
	    apply(radio_setters[i], [gladexml.get_widget(radios[i]).get_active()])
	    
	#widget.set_range(gladexml.get_widget('custom3').get_value(), gladexml.get_widget('custom2').get_value())
	gladexml.get_widget('widget_pad').destroy()
	return

    def split_path(self, widget, path, num):
	if len(path) > 0:
	    widget.osc_path[num] = path
	    widget.split_path[num] = path.split(' ')
	    i = -1 # list index from zero
	    for item in widget.split_path[num]:
		i+=1
		if item.isdigit():
		    widget.split_path[num][i] = int(item)
		if item == '%':
		    widget.sub_index[num] = i
	else:
	    widget.osc_path[num] = ''
	    widget.split_path[num] = ''	    
	return    

    def osc_send_cb(self,widget):
	#osc.Message("/filter/cutoff", [145.1232]).sendlocal(port)
	#sub in current widget value to sub location. Iterate over all paths for multid widgets
	if hasattr(widget, 'split_path'):
	    if(type(widget) == phat.Pad):
		parms = [widget.get_x().value, widget.get_y().value, widget.get_xtilt().value, widget.get_ytilt().value, widget.get_pressure().value]
		#print parms
		for i in range(len(widget.split_path)):
		    if len(widget.split_path[i]) > 0:
			widget.split_path[i][widget.sub_index[i]] = parms[i]
			osc.Message(widget.split_path[i][0], widget.split_path[i][1:len(widget.split_path)]).sendlocal(widget.port[i])
			#print 'osc.Message(', widget.split_path[i][0], widget.split_path[i][1:len(widget.split_path)], ').sendlocal(', widget.port[i],')'
	    else:
		if len(widget.split_path[0]) > 0:
		    widget.split_path[0][widget.sub_index[0]] = widget.get_value()
		    osc.Message(widget.split_path[0][0], widget.split_path[0][1:len(widget.split_path[0])]).sendlocal(widget.port[0])
		    #print 'osc.Message(', widget.split_path[0][0], widget.split_path[0][1:len(widget.split_path[0])], ').sendlocal(', widget.port[0], ')'
	return
	

    def delete_cb(self, b, widget):
	#remove current widget
	parentframe = widget.get_parent()
	parentframe.remove(widget)
	#and add the placeholder
	button = gtk.Button()
	button.connect('button_press_event', self.popup_cb)
	button.set_relief(gtk.RELIEF_HALF)
	parentframe.add(button)
	parentframe.set_label(None)
	parentframe.show_all()
	return

    def add_widget(self, type, parent_widget):
	parentframe = parent_widget.get_parent()
	parentframe.remove(parent_widget)
	
	if type == 'add_fan':
	    widget = phat.phat_hfan_slider_new_with_range(1.0, 20.0, 200000.0, 0.1)
	elif type == 'add_slider':
	    widget = phat.phat_slider_button_new_with_range(1.0, 20.0, 200000.0, 0.1, 2)
	elif type == 'add_knob':
	    widget = phat.phat_knob_new_with_range(10.0, 20.0, 200000.0, 0.1)
	elif type == 'add_pad':
	    widget = phat.Pad()
	
	widget.connect('value-changed', self.osc_send_cb)
	widget.connect('button_press_event', self.edit_popup_cb)
	widget.label = gtk.Label("Default")
	parentframe.set_label_widget(widget.label)
	parentframe.add(widget)
	parentframe.show_all()	
	

    #split the current cell vertical by creating a hbox. Everything goes in a frame first
    def vsplit_cb(self, b, widget):
	#creat a new hbox where the widget was and add the 2 buttons to it. 
	self.split('v', widget)
        return
    
    def hsplit_cb(self, b, widget):
	#creat a new vbox where the widget was and add the 2 buttons to it. 
	self.split('h', widget)
	return

    def join_cb(self, b, widget):
	#delete elements and join previous split thing FIXME type checks in here
	parentbox = widget.get_parent().get_parent()
	parentframe = parentbox.get_parent()
	parentframe.remove(parentbox)
	button1 = gtk.Button()
	button1.connect('button_press_event', self.popup_cb)
	button1.set_relief(gtk.RELIEF_HALF)
	parentframe.add(button1)
	parentframe.show_all()
	return
   
    def glade_custom_handler (self, glade, func_name, name, str1, str2, int1, int2):
        if func_name == 'PhatSliderButton':
	    temp = phat.phat_slider_button_new_with_range(100.0, 0.0, 20000.0, 0.1, 2)
	    temp.show_all()
	return temp	
    
    def split(self, dir, widget):
	if(dir == 'v'):
	    box = gtk.HBox()
	else:
	    box = gtk.VBox()
    
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
	parentframe = widget.get_parent()
	parentframe.remove(widget)
	parentframe.add(box)
	#and removet he place holder
	parentframe.show_all()
    
def save_devices():
    if os.path.exists(os.path.expanduser('~/.khagan')) == False:
	os.mkdir(os.path.expanduser('~/.khagan'))
    outfile = file(os.path.expanduser('~/.khagan/khdevice.conf'), 'w')
    for device in gtk.gdk.devices_list():
	#the src int conversion is required because the enum init func requires an int
	outfile.write(device.name + ", " + str(int(device.mode)) + "\n")
    outfile.close()
    return

#for parsing the xml, no built in str2bool
def interpret_bool(s):
    s = s.lower()
    if s in ('t', 'true', 'y', 'yes'): return True
    if s in ('f', 'false', 'n', 'no'): return False

def usage():
    print "Khagan: osc control. \n -h prints this help \n -f --file loads from specified file"
	
if __name__ == '__main__':
    ba = Khagan()
    try:
	opts, args = getopt.getopt(sys.argv[1:], "hf:", ["help", "file="])
    except getopt.GetoptError:
        # print help information and exit:
        usage()
        sys.exit(2)
    for o, a in opts:
	if o in ("-h", "--help"):
            usage()
            sys.exit()
        if o in ("-f", "--file"):
            ba.open_file(a)
    gtk.main()
    save_devices()
