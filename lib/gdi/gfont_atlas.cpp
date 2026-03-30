#include <lib/gdi/gfont_atlas.h>
#include <lib/base/eerror.h>
#include <cstring>
#include <algorithm>
#include <cstdlib>
#include <cassert>

extern "C" {
#define STB_RECT_PACK_IMPLEMENTATION
#include <include/stb_rect_pack.h>
}

gFontAtlas::gFontAtlas()
    : m_atlas_width(0)
    , m_atlas_height(0)
    , m_is_dirty(false)
{
}

gFontAtlas::~gFontAtlas()
{
}

bool gFontAtlas::init(int width, int height)
{
    m_atlas_width = width;
    m_atlas_height = height;

    m_pixmap = new gPixmap(eSize(width, height), 8);
    memset(m_pixmap->surface->data, 0, width * height);

    m_is_dirty = false;
    m_dirty_rect = eRect();

    // stb_rect_pack requires an array of nodes equal to the width of the atlas
    m_pack_nodes.resize(width);
    stbrp_init_target(&m_pack_context, width, height, m_pack_nodes.data(), m_pack_nodes.size());

    eDebug("[gFontAtlas] initialized %dx%d glyph atlas via stb_rect_pack", width, height);
    return true;
}

bool gFontAtlas::getGlyph(glyph_key_t key, glyph_uv &uv)
{
    auto it = m_glyphs.find(key);
    if (it != m_glyphs.end()) {
        uv = it->second;
        return true;
    }
    return false;
}

void gFontAtlas::addGlyph(glyph_key_t key, int width, int height, const uint8_t *data, glyph_uv &uv)
{
    if (!m_pixmap) return;
    
    if (width == 0 || height == 0) {
        // Empty space glyph
        uv.u0 = uv.v0 = uv.u1 = uv.v1 = 0.0f;
        uv.width = 0;
        uv.height = 0;
        m_glyphs[key] = uv;
        return;
    }

    stbrp_rect rect;
    rect.id = static_cast<int>(key);
    rect.w = width + 1;
    rect.h = height + 1;

    stbrp_pack_rects(&m_pack_context, &rect, 1);

    // If completely full, rebuild atlas buffer.
    if (!rect.was_packed) {
        eDebug("[gFontAtlas] ATLAS FULL! Resetting atlas...");
        m_glyphs.clear();
        memset(m_pixmap->surface->data, 0, m_atlas_width * m_atlas_height);

        stbrp_init_target(&m_pack_context, m_atlas_width, m_atlas_height, m_pack_nodes.data(), m_pack_nodes.size());
        stbrp_pack_rects(&m_pack_context, &rect, 1);

        if (!rect.was_packed) {
            eDebug("[gFontAtlas] ERROR: Glyph too large to fit in a completely empty atlas!");
            return;
        }

        m_is_dirty = true;
        m_dirty_rect = eRect(0, 0, m_atlas_width, m_atlas_height);
    }

    int px = rect.x;
    int py = rect.y;

    uint8_t *dst = (uint8_t *)m_pixmap->surface->data;
    for (int row = 0; row < height; ++row) {
        memcpy(dst + ((py + row) * m_atlas_width) + px, data + (row * width), width);
    }

    if (!m_is_dirty) {
        m_dirty_rect = eRect(px, py, width, height);
        m_is_dirty = true;
    } else {
        int min_x = std::min(m_dirty_rect.left(), px);
        int min_y = std::min(m_dirty_rect.top(), py);
        int max_x = std::max(m_dirty_rect.right(), px + width);
        int max_y = std::max(m_dirty_rect.bottom(), py + height);
        m_dirty_rect = eRect(min_x, min_y, max_x - min_x, max_y - min_y);
    }

    // Generate UVs. We use width/height (not the +1 padded sizes) so the quad wraps the glyph perfectly.
    uv.width = width;
    uv.height = height;
    uv.u0 = (float)px / (float)m_atlas_width;
    uv.v0 = (float)py / (float)m_atlas_height;
    uv.u1 = (float)(px + width) / (float)m_atlas_width;
    uv.v1 = (float)(py + height) / (float)m_atlas_height;

    m_glyphs[key] = uv;
}
