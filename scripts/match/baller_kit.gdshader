shader_type canvas_item;
// Team uniforms for baked baller sheets (tools/chibi_rig/bake.py).
// TEXTURE is the girl's sheet with her team kit painted black; kit_tex is the
// same layout holding only the kit (rgb = gray shading, a = coverage).
// Adding gray x team color on top of the black kit gives exactly what
// rendering the kit in that color would, anti-aliased edges included.
// Sprite regions come from AtlasTextures, so UV is in sheet space and samples
// both sheets at the same frame.

uniform sampler2D kit_tex : filter_linear;
uniform vec4 team_color : source_color = vec4(1.0);
uniform float kit_base = 0.9176; // kit gray that comes out as exactly team_color

varying vec4 tint;

void vertex() {
	tint = COLOR;
}

void fragment() {
	vec4 body = texture(TEXTURE, UV);
	vec4 kit = texture(kit_tex, UV);
	vec3 kit_rgb = min(kit.rgb / kit_base * team_color.rgb, vec3(1.0));
	vec3 rgb = body.rgb * body.a + kit_rgb * kit.a;
	COLOR = vec4(rgb / max(body.a, 0.0001), body.a) * tint;
}
