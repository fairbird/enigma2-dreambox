#pragma once

#include <include/stb_rect_pack.h>
#include <lib/gdi/gpixmap.h>
#include <lib/gdi/erect.h>
#include <unordered_map>
#include <vector>
#include <stdint.h>
#include <cstdint>

typedef uintptr_t glyph_key_t;

struct glyph_uv {
    float u0, v0;
    float u1, v1;
    int width, height;
};

class gFontAtlas
{
private:
    ePtr<gPixmap> m_pixmap;
    int m_atlas_width;
    int m_atlas_height;
    
    bool m_is_dirty;
    eRect m_dirty_rect;

    stbrp_context m_pack_context;
    std::vector<stbrp_node> m_pack_nodes;

    std::unordered_map<glyph_key_t, glyph_uv> m_glyphs;

public:
    gFontAtlas();
    ~gFontAtlas();

    bool init(int width = 2048, int height = 2048);
    
    bool getGlyph(glyph_key_t key, glyph_uv &uv);
    void addGlyph(glyph_key_t key, int width, int height, const uint8_t *data, glyph_uv &uv);

    gPixmap* getPixmap() const { return m_pixmap; }
    bool isDirty() const { return m_is_dirty; }
    eRect getDirtyRect() const { return m_dirty_rect; }
    void clearDirty() { m_is_dirty = false; m_dirty_rect = eRect(); }
};
