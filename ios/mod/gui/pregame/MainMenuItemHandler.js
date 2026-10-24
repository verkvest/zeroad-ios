/**
 * iOS port of 0 A.D. (GPL-2.0+; based on gui/pregame/MainMenuItemHandler.js, (c) Wildfire Games).
 * Phone landscape main menu: a left panel with the logo and two columns of 72-unit (48pt)
 * buttons; a submenu opens as a single column to the right of the panel, aligned with the
 * pressed button and clamped to the screen. Tapping the background closes the submenu.
 * Items with "iosHidden" (e.g. the Atlas Scenario Editor, not available on iOS) are skipped.
 */
export class MainMenuItemHandler
{
	constructor(closePageCallback, menuItems)
	{
		this.closePageCallback = closePageCallback;
		this.menuItems = menuItems.filter(item => !item.iosHidden);
		this.lastOpenItem = undefined;

		this.mainMenu = Engine.GetGUIObjectByName("mainMenu");
		this.mainMenuButtons = Engine.GetGUIObjectByName("mainMenuButtons");
		this.submenu = Engine.GetGUIObjectByName("submenu");
		this.submenuButtons = Engine.GetGUIObjectByName("submenuButtons");

		this.setupMenuButtons(this.mainMenuButtons.children, this.menuItems, this.Columns);
		this.setupHotkeys(this.menuItems);

		Engine.GetGUIObjectByName("closeMenuButton").onPress = this.closeSubmenu.bind(this);
		log("iOS: main menu " + this.menuItems.length + " items in " + this.Columns + " columns");
	}

	setupMenuButtons(buttons, menuItems, columns)
	{
		buttons.forEach((button, i) => {
			const item = menuItems.filter(it => !it.iosHidden)[i];
			button.hidden = !item;
			if (button.hidden)
				return;
			const row = Math.floor(i / columns);
			const col = i % columns;
			button.size = {
				"left": col ? this.Margin / 2 : 0,
				"rleft": 100 * col / columns,
				"right": col == columns - 1 ? 0 : -this.Margin / 2,
				"rright": 100 * (col + 1) / columns,
				"top": (this.ButtonHeight + this.Margin) * row,
				"bottom": (this.ButtonHeight + this.Margin) * row + this.ButtonHeight
			};
			button.caption = item.caption;
			button.tooltip = item.tooltip;
			button.enabled = item.enabled === undefined || item.enabled();
			button.onPress = this.pressButton.bind(this, item, i);
		});
	}

	pressButton(item, i)
	{
		if (this.submenu.hidden)
			this.performButtonAction(item, i);
		else
		{
			this.closeSubmenu();
			if (this.lastOpenItem && this.lastOpenItem != item)
				this.performButtonAction(item, i);
			else
				this.lastOpenItem = undefined;
		}
	}

	performButtonAction(item, i)
	{
		this.lastOpenItem = item;
		if (item.onPress)
			item.onPress(this.closePageCallback);
		else
			this.openSubmenu(i);
	}

	setupHotkeys(menuItems)
	{
		for (const i in menuItems)
		{
			const item = menuItems[i];
			if (item.onPress && item.hotkey)
				Engine.SetGlobalHotkey(item.hotkey, "Press", () => {
					this.closeSubmenu();
					item.onPress();
				});
			if (item.submenu)
				this.setupHotkeys(item.submenu);
		}
	}

	openSubmenu(i)
	{
		const items = this.menuItems[i].submenu.filter(it => !it.iosHidden);
		this.setupMenuButtons(this.submenuButtons.children, items, 1);

		const screen = this.mainMenu.parent.getComputedSize();
		const menu = this.mainMenu.getComputedSize();
		const height = (this.ButtonHeight + this.Margin) * items.length + 2 * this.Padding;
		const buttonTop = this.mainMenuButtons.children[i].getComputedSize().top - screen.top;
		const top = Math.max(this.Padding, Math.min(buttonTop - this.Padding, screen.bottom - screen.top - height - this.Padding));
		const left = menu.right - screen.left + 8;
		this.submenu.size = left + " " + top + " " + (left + this.SubmenuWidth) + " " + (top + height);
		this.submenu.hidden = false;
		log("iOS: submenu " + items.length + " items at " + Math.round(left) + "," + Math.round(top));
	}

	closeSubmenu()
	{
		this.submenu.hidden = true;
	}
}

MainMenuItemHandler.prototype.ButtonHeight = 72;
MainMenuItemHandler.prototype.Margin = 6;
MainMenuItemHandler.prototype.Padding = 6;
MainMenuItemHandler.prototype.Columns = 2;
MainMenuItemHandler.prototype.SubmenuWidth = 380;
