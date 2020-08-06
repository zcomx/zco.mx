#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
constants.py

Useful constants.

"""

# Time
SECONDS_PER_MINUTE = 60
MINUTES_PER_HOUR = 60
HOURS_PER_DAY = 24
MINUTES_PER_DAY = MINUTES_PER_HOUR * HOURS_PER_DAY
SECONDS_PER_HOUR = SECONDS_PER_MINUTE * MINUTES_PER_HOUR
SECONDS_PER_DAY = SECONDS_PER_HOUR * HOURS_PER_DAY
DAYS_PER_YEAR = 365.2425

# Length
MM_PER_CM = 10
CM_PER_M = 100
MM_PER_M = MM_PER_CM * CM_PER_M
MM_PER_INCH = 25.4
CM_PER_INCH = MM_PER_INCH / MM_PER_CM
M_PER_INCH = MM_PER_INCH / MM_PER_M
INCH_PER_MM = 1 / MM_PER_INCH
INCH_PER_CM = INCH_PER_MM * MM_PER_CM

# Weight
LB_PER_KG = 2.205
LB_PER_TON = 2000
OZ_PER_LB = 16
OZ_PER_KG = OZ_PER_LB * LB_PER_KG
KG_PER_LB = 0.454
KG_PER_TONNE = 1000


ASCII_CHARACTER = 0
ASCII_FRIENDLY_CODE = 1
ASCII_NUMERICAL_CODE = 2
ASCII_HEX_CODE = 3
ASCII_DESCRIPTION = 4

ASCII = [
        # "Display", "Friendly Code", "Numerical Code", "Hex Code",
        #       "Description"
        ("\b", "", "&#08;", "&#x08;", "Backspace"),
        ("\t", "", "&#09;", "&#x09;", "Horizontal Tab"),
        ("\n", "", "&#10;", "&#x10;", "Line feed"),
        ("\r", "", "&#13;", "&#x13;", "Carriage return"),
        (" ", "", "&#32;", "&#x20;", "space"),
        ("!", "", "&#33;", "&#x21;", "Exclamation point"),
        ('"', "&quot;", "&#34;", "&#x22;", "Double quote"),
        ("#", "", "&#35;", "&#x23;", "Number sign"),
        ("$", "", "&#36;", "&#x24;", "Dollar sign"),
        ("%", "", "&#37;", "&#x25;", "Percent sign"),
        ("&", "&amp;", "&#38;", "&#x26;", "Ampersand"),
        ("", "", "&#39;", "&#x27;", "Single quote"),
        ("(", "", "&#40;", "&#x28;", "Left parenthesis"),
        (")", "", "&#41;", "&#x29;", "Right parenthesis"),
        ("*", "", "&#42;", "&#x2A;", "Asterisk"),
        ("+", "", "&#43;", "&#x2B;", "Plus"),
        (",", "", "&#44;", "&#x2C;", "Comma"),
        ("-", "", "&#45;", "&#x2D;", "Hyphen"),
        (".", "", "&#46;", "&#x2E;", "Period"),
        ("/", "", "&#47;", "&#x2F;", "Forward slash"),
        ("0", "", "&#48;", "&#x30;", "Zero"),
        ("1", "", "&#49;", "&#x31;", "One"),
        ("2", "", "&#50;", "&#x32;", "Two"),
        ("3", "", "&#51;", "&#x33;", "Three"),
        ("4", "", "&#52;", "&#x34;", "Four"),
        ("5", "", "&#53;", "&#x35;", "Five"),
        ("6", "", "&#54;", "&#x36;", "Six"),
        ("7", "", "&#55;", "&#x37;", "Seven"),
        ("8", "", "&#56;", "&#x38;", "Eight"),
        ("9", "", "&#57;", "&#x39;", "Nine"),
        (":", "", "&#58;", "&#x3A;", "Colon"),
        (";", "", "&#59;", "&#x3B;", "Semi-colon"),
        ("<", "&lt;", "&#60;", "&#x3C;", "Less-than sign"),
        ("=", "", "&#61;", "&#x3D;", "Equal sign"),
        (">", "&gt;", "&#62;", "&#x3E;", "Greater-than sign"),
        ("?", "", "&#63;", "&#x3F;", "Question mark"),
        ("@", "", "&#64;", "&#x40;", "At-sign"),
        ("A", "", "&#65;", "&#x41;", "Capital a"),
        ("B", "", "&#66;", "&#x42;", "Capital b"),
        ("C", "", "&#67;", "&#x43;", "Capital c"),
        ("D", "", "&#68;", "&#x44;", "Capital d"),
        ("E", "", "&#69;", "&#x45;", "Capital e"),
        ("F", "", "&#70;", "&#x46;", "Capital f"),
        ("G", "", "&#71;", "&#x47;", "Capital g"),
        ("H", "", "&#72;", "&#x48;", "Capital h"),
        ("I", "", "&#73;", "&#x49;", "Capital i"),
        ("J", "", "&#74;", "&#x4A;", "Capital j"),
        ("K", "", "&#75;", "&#x4B;", "Capital k"),
        ("L", "", "&#76;", "&#x4C;", "Capital l"),
        ("M", "", "&#77;", "&#x4D;", "Capital m"),
        ("N", "", "&#78;", "&#x4E;", "Capital n"),
        ("O", "", "&#79;", "&#x4F;", "Capital o"),
        ("P", "", "&#80;", "&#x50;", "Capital p"),
        ("Q", "", "&#81;", "&#x51;", "Capital q"),
        ("R", "", "&#82;", "&#x52;", "Capital r"),
        ("S", "", "&#83;", "&#x53;", "Capital s"),
        ("T", "", "&#84;", "&#x54;", "Capital t"),
        ("U", "", "&#85;", "&#x55;", "Capital u"),
        ("V", "", "&#86;", "&#x56;", "Capital v"),
        ("W", "", "&#87;", "&#x57;", "Capital w"),
        ("X", "", "&#88;", "&#x58;", "Capital x"),
        ("Y", "", "&#89;", "&#x59;", "Capital y"),
        ("Z", "", "&#90;", "&#x5A;", "Capital z"),
        ("[", "", "&#91;", "&#x5B;", "Left square bracket"),
        ("\\", "", "&#92;", "&#x5C;", "Back slash"),
        ("]", "", "&#93;", "&#x5D;", "Right square bracket"),
        ("^", "", "&#94;", "&#x5E;", "Caret"),
        ("_", "", "&#95;", "&#x5F;", "Underscore"),
        ("`", "", "&#96;", "&#x60;", "Grave accent"),
        ("a", "", "&#97;", "&#x61;", "Lowercase a"),
        ("b", "", "&#98;", "&#x62;", "Lowercase b"),
        ("c", "", "&#99;", "&#x63;", "Lowercase c"),
        ("d", "", "&#100;", "&#x64;", "Lowercase d"),
        ("e", "", "&#101;", "&#x65;", "Lowercase e"),
        ("f", "", "&#102;", "&#x66;", "Lowercase f"),
        ("g", "", "&#103;", "&#x67;", "Lowercase g"),
        ("h", "", "&#104;", "&#x68;", "Lowercase h"),
        ("i", "", "&#105;", "&#x69;", "Lowercase i"),
        ("j", "", "&#106;", "&#x6A;", "Lowercase j"),
        ("k", "", "&#107;", "&#x6B;", "Lowercase k"),
        ("l", "", "&#108;", "&#x6C;", "Lowercase l"),
        ("m", "", "&#109;", "&#x6D;", "Lowercase m"),
        ("n", "", "&#110;", "&#x6E;", "Lowercase n"),
        ("o", "", "&#111;", "&#x6F;", "Lowercase o"),
        ("p", "", "&#112;", "&#x70;", "Lowercase p"),
        ("q", "", "&#113;", "&#x71;", "Lowercase q"),
        ("r", "", "&#114;", "&#x72;", "Lowercase r"),
        ("s", "", "&#115;", "&#x73;", "Lowercase s"),
        ("t", "", "&#116;", "&#x74;", "Lowercase t"),
        ("u", "", "&#117;", "&#x75;", "Lowercase u"),
        ("v", "", "&#118;", "&#x76;", "Lowercase v"),
        ("w", "", "&#119;", "&#x77;", "Lowercase w"),
        ("x", "", "&#120;", "&#x78;", "Lowercase x"),
        ("y", "", "&#121;", "&#x79;", "Lowercase y"),
        ("z", "", "&#122;", "&#x7A;", "Lowercase z"),
        ("{", "", "&#123;", "&#x7B;", "Left curly brace"),
        ("|", "", "&#124;", "&#x7C;", "Vertical bar"),
        ("}", "", "&#125;", "&#x7D;", "Right curly brace"),
        ("~", "&tilde;", "&#126;", "&#x7E;", "tilde"),
        ("", "", "&#127;", "&#x7F;", "Not defined"),
        ("", "", "&#128;", "&#x80;", "Euro"),
        ("", "", "&#129;", "&#x81;", "Unknown"),
        ("‚", "&sbquo;", "&#130;", "&#x82;", "Single low-quote"),
        ("", "", "&#131;", "&#x83;",
            "Function symbol (lowercase f with hook)"),
        ("„", "&dbquo;", "&#132;", "&#x84;", "Double low-quote"),
        ("", "", "&#133;", "&#x85;", "Elipsis"),
        ("†", "&dagger;", "&#134;", "&#x86;", "Dagger"),
        ("‡", "&Dagger;", "&#135;", "&#x87;", "Double dagger"),
        ("", "", "&#136;", "&#x88;", "Hatchek"),
        ("‰", "&permil;", "&#137;", "&#x89;", "Per million symbol"),
        ("", "", "&#138;", "&#x8A;", "Capital esh"),
        ("‹", "&lsaquo;", "&#139;", "&#x8B;", "Left single angle quote"),
        ("", "", "&#140;", "&#x8C;", "OE ligature"),
        ("", "", "&#141;", "&#x8D;", "Unknown"),
        ("", "", "&#142;", "&#x8E;", "Capital "),
        ("", "", "&#143;", "&#x8F;", "Unknown"),
        ("", "", "&#144;", "&#x90;", "Unknown"),
        ("‘", "&lsquo;", "&#145;", "&#x91;", "Left single-quote"),
        ("’", "&rsquo;", "&#146;", "&#x92;", "Right single-quote"),
        ("“", "&ldquo;", "&#147;", "&#x93;", "Left double-quote"),
        ("”", "&rdquo;", "&#148;", "&#x94;", "Right double-quote"),
        ("", "", "&#149;", "&#x95;", "Small bullet"),
        ("", "&ndash;", "&#150;", "&#x96;", "En dash"),
        ("", "&mdash;", "&#151;", "&#x97;", "Em dash"),
        ("", "&tilde", "&#152;", "&#x98;", "Tilde"),
        ("", "&trade;", "&#153;", "&#x99;", "Trademark"),
        ("", "", "&#154;", "&#x9A;", "Lowercase esh"),
        ("›", "&rsaquo;", "&#155;", "&#x9B;", "Right single angle quote"),
        ("", "", "&#156;", "&#x9C;", "oe ligature"),
        ("", "", "&#157;", "&#x9D;", "Unknown"),
        ("", "", "&#158;", "&#x9E;", "Lowercase "),
        ("", "&Yuml;", "&#159;", "&#x9F;", "Uppercase y-umlaut"),
        ("", "&nbsp;", "&#160;", "&#xA0;", "Non-breaking space"),
        ("¡", "&iexcl;", "&#161;", "&#xA1;", "Inverted exclamation point"),
        ("¢", "&cent;", "&#162;", "&#xA2;", "Cent"),
        ("£", "&pound;", "&#163;", "&#xA3;", "Pound currency sign"),
        ("¤", "&curren;", "&#164;", "&#xA4;", "Currency sign"),
        ("¥", "&yen;", "&#165;", "&#xA5;", "Yen currency sign"),
        ("¦", "&brvbar;", "&#166;", "&#xA6;", "Broken vertical bar"),
        ("§", "&sect;", "&#167;", "&#xA7;", "Section symbol"),
        ("¨", "&uml;", "&#168;", "&#xA8;", "Umlaut (Diaeresis)"),
        ("©", "&copy;", "&#169;", "&#xA9;", "Copyright"),
        ("ª", "&ordf;", "&#170;", "&#xAA;",
            "Feminine ordinal indicator (superscript lowercase a)"),
        ("«", "&laquo;", "&#171;", "&#xAB;", "Left angle quote"),
        ("¬", "&not;", "&#172;", "&#xAC;", "Not sign"),
        ("­", "&shy;", "&#173;", "&#xAD;", "Soft hyphen"),
        ("®", "&reg;", "&#174;", "&#xAE;", "Registered sign"),
        ("¯", "&macr;", "&#175;", "&#xAF;", "Macron"),
        ("°", "&deg;", "&#176;", "&#xB0;", "Degree sign"),
        ("±", "&plusmn;", "&#177;", "&#xB1;", "Plus/minus sign"),
        ("²", "&sup2;", "&#178;", "&#xB2;", "Superscript 2"),
        ("³", "&sup3;", "&#179;", "&#xB3;", "Superscript 3"),
        ("´", "", "&#180;", "&#xB4;", "Acute accent"),
        ("µ", "&micro;", "&#181;", "&#xB5;", "Micro sign"),
        ("¶", "&para;", "&#182;", "&#xB6;", "Pilcrow sign (paragraph)"),
        ("·", "&middot;", "&#183;", "&#xB7;", "Middle dot"),
        ("¸", "&cedil;", "&#184;", "&#xB8;", "Cedilla"),
        ("¹", "&sup1;", "&#185;", "&#xB9;", "Superscript 1"),
        ("º", "&ordm;", "&#186;", "&#xBA;",
            "Masculine ordinal indicator (superscript o)"),
        ("»", "&raquo;", "&#187;", "&#xBB;", "Right angle quote"),
        ("¼", "&frac14;", "&#188;", "&#xBC;", "One quarter fraction"),
        ("½", "&frac12;", "&#189;", "&#xBD;", "One half fraction"),
        ("¾", "&frac34;", "&#190;", "&#xBE;", "Three quarters fraction"),
        ("¿", "&iquest;", "&#191;", "&#xBF;", "Inverted question mark"),
        ("À", "&Agrave;", "&#192;", "&#xC0;", "A grave accent"),
        ("Á", "&Aacute;", "&#193;", "&#xC1;", "A accute accent"),
        ("Â", "&Acirc;", "&#194;", "&#xC2;", "A circumflex"),
        ("Ã", "&Atilde;", "&#195;", "&#xC3;", "A tilde"),
        ("Ä", "&Auml;", "&#196;", "&#xC4;", "A umlaut"),
        ("Å", "&Aring;", "&#197;", "&#xC5;", "A ring"),
        ("Æ", "&AElig;", "&#198;", "&#xC6;", "AE ligature"),
        ("Ç", "&Ccedil;", "&#199;", "&#xC7;", "C cedilla"),
        ("È", "&Egrave;", "&#200;", "&#xC8;", "E grave"),
        ("É", "&Eacute;", "&#201;", "&#xC9;", "E acute"),
        ("Ê", "&Ecirc;", "&#202;", "&#xCA;", "E circumflex"),
        ("Ë", "&Euml;", "&#203;", "&#xCB;", "E umlaut"),
        ("Ì", "&Igrave;", "&#204;", "&#xCC;", "I grave"),
        ("Í", "&Iacute;", "&#205;", "&#xCD;", "I acute"),
        ("Î", "&Icirc;", "&#206;", "&#xCE;", "I circumflex"),
        ("Ï", "&Iuml;", "&#207;", "&#xCF;", "I umlaut"),
        ("Ð", "&ETH;", "&#208;", "&#xD0;", "Eth"),
        ("Ñ", "&Ntilde;", "&#209;", "&#xD1;", "N tilde (enye)"),
        ("Ò", "&Ograve;", "&#210;", "&#xD2;", "O grave"),
        ("Ó", "&Oacute;", "&#211;", "&#xD3;", "O acute"),
        ("Ô", "&Ocirc;", "&#212;", "&#xD4;", "O circumflex"),
        ("Õ", "&Otilde;", "&#213;", "&#xD5;", "O tilde"),
        ("Ö", "&Ouml;", "&#214;", "&#xD6;", "O umlaut"),
        ("×", "&times;", "&#215;", "&#xD7;", "Multiplication sign"),
        ("Ø", "&Oslash;", "&#216;", "&#xD8;", "O slash"),
        ("Ù", "&Ugrave;", "&#217;", "&#xD9;", "U grave"),
        ("Ú", "&Uacute;", "&#218;", "&#xDA;", "U acute"),
        ("Û", "&Ucirc;", "&#219;", "&#xDB;", "U circumflex"),
        ("Ü", "&Uuml;", "&#220;", "&#xDC;", "U umlaut"),
        ("Ý", "&Yacute;", "&#221;", "&#xDD;", "Y acute"),
        ("Þ", "&THORN;", "&#222;", "&#xDE;", "Thorn"),
        ("ß", "&szlig;", "&#223;", "&#xDF;", "SZ ligature"),
        ("à", "&agrave;", "&#224;", "&#xE0;", "a grave"),
        ("á", "&aacute;", "&#225;", "&#xE1;", "a acute"),
        ("â", "&acirc;", "&#226;", "&#xE2;", "a circumflex"),
        ("ã", "&atilde;", "&#227;", "&#xE3;", "a tilde"),
        ("ä", "&auml;", "&#228;", "&#xE4;", "a umlaut"),
        ("å", "&aring;", "&#229;", "&#xE5;", "a ring"),
        ("æ", "&aelig;", "&#230;", "&#xE6;", "ae ligature"),
        ("ç", "&ccedil;", "&#231;", "&#xE7;", "c cedilla"),
        ("è", "&egrave;", "&#232;", "&#xE8;", "e grave"),
        ("é", "&eacute;", "&#233;", "&#xE9;", "e acute"),
        ("ê", "&ecirc;", "&#234;", "&#xEA;", "e circumflex"),
        ("ë", "&euml;", "&#235;", "&#xEB;", "e umlaut"),
        ("ì", "&igrave;", "&#236;", "&#xEC;", "i grave"),
        ("í", "&iacute;", "&#237;", "&#xED;", "i acute"),
        ("î", "&icirc;", "&#238;", "&#xEE;", "i circumflex"),
        ("ï", "&iuml;", "&#239;", "&#xEF;", "i umlaut"),
        ("ð", "&eth;", "&#240;", "&#xF0;", "eth"),
        ("ñ", "&ntilde;", "&#241;", "&#xF1;", "n tilde"),
        ("ò", "&ograve;", "&#242;", "&#xF2;", "o grave"),
        ("ó", "&oacute;", "&#243;", "&#xF3;", "o acute"),
        ("ô", "&ocirc;", "&#244;", "&#xF4;", "o circumflex"),
        ("õ", "&otilde;", "&#245;", "&#xF5;", "o tilde"),
        ("ö", "&ouml;", "&#246;", "&#xF6;", "o umlaut"),
        ("÷", "&divide;", "&#247;", "&#xF7;", "Division symbol"),
        ("ø", "&oslash;", "&#248;", "&#xF8;", "o slash"),
        ("ù", "&ugrave;", "&#249;", "&#xF9;", "u grave"),
        ("ú", "&uacute;", "&#250;", "&#xFA;", "u acute"),
        ("û", "&ucirc;", "&#251;", "&#xFB;", "u circumflex"),
        ("ü", "&uuml;", "&#252;", "&#xFC;", "u umlaut"),
        ("ý", "&yacute;", "&#253;", "&#xFD;", "y acute"),
        ("þ", "&thorn;", "&#254;", "&#xFE;", "thorn"),
        ("ÿ", "&yuml;", "&#255;", "&#xFF;", "y umlaut"),
        ("℅", "", "&#8453;", "&#x2105;", "Care Of"),
        ("ⁿ", "", "&#8319;", "&#x207F;", "Superscript N"),
        ("―", "", "&#8213;", "&#x2015;", "Horizontal Bar"),
        ("‣", "", "&#8227;", "&#x2023;", "Triangle Bullet"),
        ("‾", "&oline;", "&#8254;", "&#x203E;", "Overline"),
        ("‼", "", "&#8252;", "&#x203C;", "Double Exclamation Point"),
        ("№", "", "&#8470;", "&#x2116;", "Number Word"),
        ("♠", "&spades;", "&#9824;", "&#x2660;", "Spade card suit"),
        ("♣", "&clubs;", "&#9827;", "&#x2663;", "Clubs card suit"),
        ("♦", "&diams;", "&#9830;", "&#x2666;", "Diamonds card suit"),
        ("♥", "&hearts;", "&#9829;", "&#x2665;", "Hearts card suit"),
        ("←", "&larr;", "&#8592;", "&#x2190;", "Left arrow"),
        ("→", "&rarr;", "&#8594;", "&#x2192;", "Right arrow"),
        ("↑", "&uarr;", "&#8593;", "&#x2191;", "Up arrow"),
        ("↓", "&darr;", "&#8595;", "&#x2193;", "Down arrow"),
        ("♀", "", "&#9792;", "&#x2640;", "Female Indicator"),
        ("♂", "", "&#9794;", "&#x2642;", "Male Indicator"),
        ("♩", "", "&#9833;", "&#x2669;", "Quarter Note"),
        ("♪", "", "&#9834;", "&#x266A;", "Eighth Note"),
        ("♬", "", "&#9836;", "&#x266C;", "Two Eighth Notes"),
        ("♭", "", "&#9837;", "&#x266D;", "Flat"),
        ("♯", "", "&#9839;", "&#x266F;", "Sharp"),
        ]


def ascii_lookup(char, want):
    """Lookup ascii character in ASCII table.

    Args:
        char: string, single character.
        want: integer, 0 to 4, ASCII_CHARACTER to ASCII_DESCRIPTION

    Returns:
        string, the value in ASCII lookup table.
    """
    for c in ASCII:
        if char == c[ASCII_CHARACTER]:
            return c[want]
