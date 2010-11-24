.PHONY: all clean install uninstall

all:
	@echo "It's all there, just an ls away!"

clean:
	rm -f *~

install:
	mkdir -p $(DESTDIR)/usr/share/calibre-utils/
	cp webpage2calibre wikipedia2calibre remove-nontoc-links.py $(DESTDIR)/usr/share/calibre-utils/
	cp webpage-icon.png wikipedia-icon.png $(DESTDIR)/usr/share/calibre-utils/
	cp webpage-cover-template.jpg wikipedia-cover-template.jpg $(DESTDIR)/usr/share/calibre-utils/
	mkdir -p $(DESTDIR)/usr/share/doc/calibre-utils/
	cp AUTHORS COPYING README $(DESTDIR)/usr/share/doc/calibre-utils/
	test -d $(DESTDIR)/usr/bin/ || mkdir -p $(DESTDIR)/usr/bin/

	# A symbolic link isn't the same... The absolute path is stored into
	# it, so my computer's path would remain into it; a script seems a
	# better choice.
	echo /usr/share/calibre-utils/webpage2calibre > $(DESTDIR)/usr/bin/webpage2calibre
	chmod +x $(DESTDIR)/usr/bin/webpage2calibre
	echo /usr/share/calibre-utils/wikipedia2calibre > $(DESTDIR)/usr/bin/wikipedia2calibre
	chmod +x $(DESTDIR)/usr/bin/wikipedia2calibre

	test -d $(DESTDIR)/usr/share/applications/ || mkdir -p $(DESTDIR)/usr/share/applications/
	cp webpage2calibre.desktop $(DESTDIR)/usr/share/applications/
	cp wikipedia2calibre.desktop $(DESTDIR)/usr/share/applications/
	update-desktop-database || true

uninstall:
	rm -f $(DESTDIR)/usr/bin/webpage2calibre
	rm -f $(DESTDIR)/usr/bin/wikipedia2calibre
	rm -fr $(DESTDIR)/usr/share/calibre-utils/
	rm -fr $(DESTDIR)/usr/share/doc/calibre-utils/
	rm -f $(DESTDIR)/usr/share/applications/webpage2calibre.desktop
	rm -f $(DESTDIR)/usr/share/applications/wikipedia2calibre.desktop
	update-desktop-database || true
