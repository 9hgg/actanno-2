    def curFrame(self):
	name,ext=os.path.splitext(self.filenames[self.curFrameNr])
	if ext == "png":
		png = Image.open(self.filenames[self.curFrameNr])
		png.load()

		background = Image.new("RGB", png.size, (255, 255, 255))
		background.paste(png, mask=png.split()[3]) # 3 is the alpha channel

		background.save('foo.jpg', 'JPEG', quality=80)
		self.curImage = background
	elif ext == "jpg":
        	self.curImage = Image.open(self.filenames[self.curFrameNr])
	else:
		print "Extension not supported but trying anyway."
        	self.curImage = Image.open(self.filenames[self.curFrameNr])
       	# print "frame nr. ",self.curFrameNr, "=",self.filenames[self.curFrameNr]
        return self.curImage
