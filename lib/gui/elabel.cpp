#include <lib/gui/elabel.h>
#include <lib/gdi/font.h>

eLabel::eLabel(eWidget *parent, int markedPos): eWidget(parent)
{
	m_pos = markedPos;
	ePtr<eWindowStyle> style;
	getStyle(style);

	style->getFont(eWindowStyle::fontStatic, m_font);

		/* default to topleft alignment */
	m_valign = alignTop;
	m_halign = alignBidi;

	m_have_foreground_color = 0;
	m_have_shadow_color = 0;

	m_nowrap = 0;
	m_border_size = 0;

	m_text_offset = 0;
}

int eLabel::event(int event, void *data, void *data2)
{
	switch (event)
	{
	case evtPaint:
	{
		ePtr<eWindowStyle> style;

		getStyle(style);

		eWidget::event(event, data, data2);

		gPainter &painter = *(gPainter*)data2;

		painter.setFont(m_font);
		style->setStyle(painter, eWindowStyle::styleLabel);

		if (m_have_shadow_color)
			painter.setForegroundColor(m_shadow_color);
		else if (m_have_foreground_color)
			painter.setForegroundColor(m_foreground_color);

		int flags = 0;
		if (m_valign == alignTop)
			flags |= gPainter::RT_VALIGN_TOP;
		else if (m_valign == alignCenter)
			flags |= gPainter::RT_VALIGN_CENTER;
		else if (m_valign == alignBottom)
			flags |= gPainter::RT_VALIGN_BOTTOM;

		if (m_halign == alignLeft)
			flags |= gPainter::RT_HALIGN_LEFT;
		else if (m_halign == alignCenter)
			flags |= gPainter::RT_HALIGN_CENTER;
		else if (m_halign == alignRight)
			flags |= gPainter::RT_HALIGN_RIGHT;
		else if (m_halign == alignBlock)
			flags |= gPainter::RT_HALIGN_BLOCK;

		if (!m_nowrap)
			flags |= gPainter::RT_WRAP;

		int x = m_padding.x();
		int y = m_padding.y();

		int w = size().width() - m_padding.right();
		int h = size().height() - m_padding.bottom();

		auto position = eRect(x, y, w, h);
		/* if we don't have shadow, m_shadow_offset will be 0,0 */
		auto shadowposition = eRect(position.x()-m_shadow_offset.x(),position.y()-m_shadow_offset.y(),position.width()-m_shadow_offset.x(),position.height()-m_shadow_offset.y());
		painter.renderText(shadowposition, m_text, flags, m_border_color, m_border_size, m_pos, &m_text_offset);

		if (m_have_shadow_color)
		{
			if (!m_have_foreground_color)
				style->setStyle(painter, eWindowStyle::styleLabel);
			else
				painter.setForegroundColor(m_foreground_color);
			painter.setBackgroundColor(m_shadow_color);
			painter.renderText(position, m_text, flags, gRGB(), 0, m_pos);
		}

		return 0;
	}
	case evtChangedFont:
	case evtChangedText:
	case evtChangedAlignment:
	case evtChangedMarkedPos:
		invalidate();
		return 0;
	default:
		return eWidget::event(event, data, data2);
	}
}

void eLabel::setText(const std::string &string)
{
	if (m_text == string)
		return;
	m_text = string;
	event(evtChangedText);
}

void eLabel::setMarkedPos(int markedPos)
{
	m_pos = markedPos;
	event(evtChangedMarkedPos);
}

void eLabel::setFont(gFont *font)
{
	m_font = font;
	event(evtChangedFont);
}

gFont* eLabel::getFont()
{
	return m_font;
}

void eLabel::setVAlign(int align)
{
	m_valign = align;
	event(evtChangedAlignment);
}

void eLabel::setHAlign(int align)
{
	m_halign = align;
	event(evtChangedAlignment);
}

void eLabel::setForegroundColor(const gRGB &col)
{
	if ((!m_have_foreground_color) || (m_foreground_color != col))
	{
		m_foreground_color = col;
		m_have_foreground_color = 1;
		invalidate();
	}
}

void eLabel::setShadowColor(const gRGB &col)
{
	if ((!m_have_shadow_color) || (m_shadow_color != col))
	{
		m_shadow_color = col;
		m_have_shadow_color = 1;
		invalidate();
	}
}

void eLabel::setShadowOffset(const ePoint &offset)
{
	m_shadow_offset = offset;
}

void eLabel::setBorderColor(const gRGB &col)
{
	if (m_border_color != col)
	{
		m_border_color = col;
		invalidate();
	}
}

void eLabel::setBorderWidth(int size)
{
	m_border_size = size;
}

void eLabel::setNoWrap(int nowrap)
{
	if (m_nowrap != nowrap)
	{
		m_nowrap = nowrap;
		invalidate();
	}
}

void eLabel::clearForegroundColor()
{
	if (m_have_foreground_color)
	{
		m_have_foreground_color = 0;
		invalidate();
	}
}

eSize eLabel::calculateSize()
{
	return calculateTextSize(m_font, m_text, size(), m_nowrap);
}

eSize eLabel::calculateTextSize(gFont* font, const std::string &string, eSize targetSize, bool nowrap)
{
	// Calculate text size for a piece of text without creating an eLabel instance 
	// this avoids the side effect of "invalidate" being called on the parent container
	// during the setup of the font and text on the eLabel
	eTextPara para(eRect(0, 0, targetSize.width(), targetSize.height()));
	para.setFont(font);
	para.renderString(string.empty() ? 0 : string.c_str(), nowrap ? 0 : RS_WRAP);
	return para.getBoundBox().size();
}
