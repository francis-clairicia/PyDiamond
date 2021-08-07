MYPYGAME_DIR	=	my_pygame

SRC				=	$(MYPYGAME_DIR)/__init__.py			\
					$(MYPYGAME_DIR)/_gradients.py		\
					$(MYPYGAME_DIR)/animation.py		\
					$(MYPYGAME_DIR)/button.py			\
					$(MYPYGAME_DIR)/checkbox.py			\
					$(MYPYGAME_DIR)/clickable.py		\
					$(MYPYGAME_DIR)/clock.py			\
					$(MYPYGAME_DIR)/colors.py			\
					$(MYPYGAME_DIR)/configuration.py	\
					$(MYPYGAME_DIR)/cursor.py			\
					$(MYPYGAME_DIR)/drawable.py			\
					$(MYPYGAME_DIR)/gradients.py		\
					$(MYPYGAME_DIR)/image.py			\
					$(MYPYGAME_DIR)/keyboard.py			\
					$(MYPYGAME_DIR)/mouse.py			\
					$(MYPYGAME_DIR)/path.py				\
					$(MYPYGAME_DIR)/resource.py			\
					$(MYPYGAME_DIR)/scene.py			\
					$(MYPYGAME_DIR)/shape.py			\
					$(MYPYGAME_DIR)/sprite.py			\
					$(MYPYGAME_DIR)/surface.py			\
					$(MYPYGAME_DIR)/text.py				\
					$(MYPYGAME_DIR)/theme.py			\
					$(MYPYGAME_DIR)/window.py			\

STUBS			=	$(SRC:.py=.pyi)

all:	stubs

stubs:	$(STUBS)
	black $^

%.pyi:	%.py
	@stubgen -o . --include-private --export-less $<

fclean clean:
	$(RM) $(STUBS)
.PHONY: fclean clean

re::	fclean
re::	stubs
.PHONY: re

