function scoutsssDialogsInit() {
    jQuery(function() {
        jQuery(document).on("click", ".scoutsss-dialog-close", function() {
            ["AD98ED", "7BBB84", "3F7172", "0223EF", "B61D16"].includes(jQuery(this).data("code")) || btn.show(), "avatar" == jQuery(this).data("onclose") && (btn.css("background", ""), btn.find("div").hide(), btn.find("img").parent().show(), btn.find(".dialog-icon").show()), setc("closed-" + jQuery(this).data("code"), 1, 365), jQuery(this).closest(".scoutsss-dialog-container").hide(), console.log("close")
        }), jQuery(document).on("click", ".scoutsss-dialog-refresh", function() {
            jQuery(this).closest(".scoutsss-dialog-container").find("iframe").hide(), jQuery(this).closest(".scoutsss-dialog-container").find(".container-loader").show(), jQuery(this).closest(".scoutsss-dialog-container").find("iframe").attr("src", jQuery(this).closest(".scoutsss-dialog-container").find("iframe").attr("src"))
        });
        var t = {
            "-webkit-box-shadow": "-12px 14px 40px -14px rgba(102,102,102,1)",
            "-moz-box-shadow": "-12px 14px 40px -14px rgba(102,102,102,1)",
            "box-shadow": "-12px 14px 40px -14px rgba(102,102,102,1)"
        };
        jQuery(".scoutsss-dialog").each(function() {
            if (id = "scoutsss-dialog-" + jQuery(this).data("code") + "-" + jQuery(this).data("placement"), 0 == jQuery("#" + id).length) {
                btn = jQuery("<div>"), btn.addClass("scoutsss-dialog-btn");
                var e = jQuery(this).data("bgcolor");
                if (btn.css({
                    background: e,
                    "z-index": "9999",
                    "font-family": "sans-serif",
                    color: "white",
                    "text-align": "center",
                    "font-weight": "700",
                    position: "fixed",
                    cursor: "pointer"
                }), "small" == jQuery(this).data("size") && btn.css({
                    "min-width": "100px",
                    clear: "both",
                    padding: "10px",
                    "font-size": "14px",
                    "border-radius": "15px"
                }), "medium" == jQuery(this).data("size") && btn.css({
                    "min-width": "200px",
                    clear: "both",
                    padding: "20px",
                    "font-size": "16px",
                    "border-radius": "25px"
                }), "large" == jQuery(this).data("size") && btn.css({
                    "min-width": "300px",
                    clear: "both",
                    padding: "30px",
                    "font-size": "22px",
                    "border-radius": "50px"
                }), btn.append(jQuery("<div>")), btn.find("div").css("position", "relative"), img = jQuery("<img>"), img.attr("src", jQuery(this).data("img")), img.addClass("dialog-icon"), jQuery(this).data("img") && ("0" == jQuery(this).data("showicon") && img.hide(), btn.find("div").append(img)), "large" == jQuery(this).data("size") && btn.find("img").css({
                    position: "absolute",
                    top: "-35px",
                    left: "-50px",
                    width: "70px",
                    "border-radius": "35px"
                }), "medium" == jQuery(this).data("size") && btn.find("img").css({
                    position: "absolute",
                    top: "-25px",
                    left: "-35px",
                    width: "50px",
                    "border-radius": "25px"
                }), btnTexts = new String(jQuery(this).data("title")), btnTexts = btnTexts.split("|"), textTurn = 0, btn.css("box-sizing", "content-box"), btn.find("div").attr("style", "position: relative;box-sizing: content-box; -moz-box-sizing: content-box; -webkit-box-sizing: content-box;"), btn.find("div").append(jQuery("<div>").addClass("dialog-btn-text").attr("style", "padding-left: 20px;padding-right: 20px;box-sizing: content-box; -moz-box-sizing: content-box; -webkit-box-sizing: content-box;").html(btnTexts[textTurn])), btnTexts.length > 0 && setInterval(function() {
                    textTurn++, textTurn == btnTexts.length && (textTurn = 0), jQuery(".dialog-btn-text").html(btnTexts[textTurn])
                }, 1e3 * parseInt(jQuery(this).data("delay"))), btn.css(scoutsssDialogsGetPlacement(jQuery(this).data("placement"))), arrow = jQuery("<div>"), arrow.css({
                    width: "0px",
                    height: "0px",
                    "border-left": "20px solid transparent",
                    "border-right": "20px solid transparent",
                    transform: "rotate(140deg)",
                    position: "absolute",
                    left: "20px",
                    bottom: "-15px",
                    "border-top": "20px solid " + e
                }), btn.append(arrow), code = jQuery(this).data("code"), video = jQuery(this).data("video"), videoURL = jQuery(this).data("videourl"), videBtnText = 1 == jQuery(this).data("videobubble") ? "" : jQuery(this).data("title"), videoDelay = jQuery(this).data("videodelay"), videoBtnPos = "", "40C6D9" != code && "7BBB84" != code && 1 != video || ("40C6D9" != code && "7BBB84" != code || (code = "7BBB84", "Hast du Fragen?" == jQuery(this).data("title") ? videBtnText = "Klick hier" : videBtnText = "Click here", videoURL = "https://test.scoutsss.com/video-btn-2.mp4", videoBtnPos = isMobile ? "left: 50px;bottom: 10px;" : "left: 100px;bottom: 20px;"), id = "scoutsss-dialog-" + code + "-" + jQuery(this).data("placement"), videoBtnHTML = '<div id="scoutsss-video-btn-' + code + '" data-code="' + code + '" style="position: fixed;z-index: 999;' + videoBtnPos + 'width: 150px;height: 150px;text-align: center;vertical-align: middle;display: table-cell;cursor: pointer;"><video style="border-radius: 80px;border: 7px solid ' + e + ';" id="scoutsss-video-' + code + '" width="150" height="150" muted playsinline loop autoplay webkit-playsinline><source src="' + videoURL + '" type="video/mp4"></video><div id="scoutsss-text-container-' + code + '" style="position: relative;"><center><span style="color: ' + e + '; font-size: 18px;font-weight: bold;position: absolute;text-align: center;left: 0px;right:0;margin-right: auto;margin-left: auto;top: -45px;z-index: 999;">' + videBtnText + "</span></center></div></div>", videoBtnContainer = jQuery("<div>").html(videoBtnHTML), videoBtn = videoBtnContainer.find("#scoutsss-video-btn-" + code), "7BBB84" != code && videoBtn.css(scoutsssDialogsGetPlacement(jQuery(this).data("placement"))), btn.hide(), videoBtn.on("click", function(t) {
                    console.log("videBtn code %s", jQuery(this).data("code")), "7BBB84" == jQuery(this).data("code") ? (aliasBtn = jQuery("#scoutsss-dialog-" + jQuery(this).data("code") + "-bottom-left"), aliasBtn.trigger("click")) : btn.trigger("click"), void 0 == t.isTrigger ? (videoBtn.hide(), aliasBtn.show(), aliasBtn.css("background", ""), aliasBtn.find("div").hide(), aliasBtn.find("img").parent().show()) : (videoBtn.show(), aliasBtn.hide(), aliasBtn.css("background", jQuery(this).data("bgcolor")), aliasBtn.find("div").show())
                }), videoBtn.hide(), jQuery("body").append(videoBtn), videoDelay = parseInt(videoDelay), videoDelay > -1 || (videoDelay = 0), setTimeout(function() {
                    videoBtn.fadeIn(), videoElement = document.getElementById("scoutsss-video-" + code), videoElement && videoElement.play()
                }, 1e3 * videoDelay)), btn.attr("id", id), btn.attr("placement", jQuery(this).data("placement")), btn.attr("code", code), btn.attr("draggable", jQuery(this).data("draggable")), btn.attr("transparent", jQuery(this).data("transparent")), btn.attr("header", jQuery(this).data("header")), btn.attr("notifications", jQuery(this).data("notifications")), btn.attr("hidden", jQuery(this).data("hidden")), btn.attr("onclose", jQuery(this).data("onclose")), 1 == jQuery(this).data("videoclickicon") && (clickIcon = jQuery("<img>"), clickIcon.attr("src", "/images/click.png"), clickIcon.attr("width", 70), clickIcon.css("position", "absolute"), clickIcon.css("top", "85px"), clickIcon.css("left", "40px"), 1 == video && videoBtn.append(clickIcon)), 1 == jQuery(this).data("videobubble")) {
                    bubble = btn.clone(!0, !0), bubble.find("img").hide(), bubble.css("position", "absolute"), bubble.css("top", "-60px"), bubble.css("left", "60px"), bubble.css({
                        bottom: ""
                    }), bubble.css("min-height", "20px"), bubble.show();
                    try {
                        jQuery(this).data("placement").includes("right") && videoBtn.css("right", "150px")
                    } catch (t) {}
                    1 == video && videoBtn.append(bubble)
                }
                1 == jQuery(this).data("notifications") && (badge = jQuery("<div>"), badge.css("width", "20px"), badge.css("height", "15px"), badge.css("background", "#cc0000"), badge.css("padding", "5px"), badge.css("border-radius", "3px"), badge.css("color", "white"), badge.css("text-align", "center"), badge.css("position", "absolute"), badge.css("top", "-10px"), badge.css("right", "0"), badge.text(1), btn.append(badge), 1 == video && videoBtn.append(badge)), "true" == jQuery(this).data("hidden") && btn.hide(), "centered" != jQuery(this).data("placement") && "top-centered" != jQuery(this).data("placement") && "bottom-centered" != jQuery(this).data("placement") || (widthSpan = jQuery("<span>").text(jQuery(this).data("title")).hide(), jQuery("body").append(widthSpan), btn.css({
                    "max-width": widthSpan.width() + 150 + "px"
                })), clickEvent = jQuery(this).data("click"), btn.on("click", function(e, i) {
                    if ("landing" == clickEvent) return window.open(webUrl + "/dlink?code=" + code), !1;
                    if (0 == jQuery("#" + jQuery(this).attr("id") + "-container").length) {
                        container = jQuery("<div>"), height = isMobile ? jQuery(window).height() - 10 : Math.round(jQuery(window).height()), containerPlacement = scoutsssDialogsGetPlacement(jQuery(this).attr("placement")), container.css(containerPlacement), container.css({
                            position: "fixed",
                            "border-radius": "10px",
                            "z-index": "999999",
                            width: isMobile ? "100%" : "400px",
                            height: height + "px",
                            background: "true" == jQuery(this).attr("transparent") ? "transparent" : "white"
                        }), isMobile && container.css({
                            "-webkit-overflow-scrolling": "touch",
                            "overflow-y": "scroll"
                        }), "top" in containerPlacement && container.css("top", isMobile ? "0px" : "20px"), "bottom" in containerPlacement && container.css("bottom", "0px"), "true" == jQuery(this).attr("transparent") || container.css(t), container.addClass("scoutsss-dialog-container");
                        var s = getct();
                        urlCtV && (s = urlCtV, console.log(s)), isSafari && (savedsh = getc("sh"), console.log("savedsh"), console.log(savedsh), savedsh || (setc("sh", Math.random().toString(36).substr(2), 365), console.log("ns"), console.log(getc("sh")))), "D1099D" == jQuery(this).attr("code") && (webUrl = "https://dialog.scoutsss.com");
                        var o = webUrl + "/dlink?embedded=1" + ("hidden" == jQuery(this).attr("header") ? "&fh=-1" : "") + ("fixed" == jQuery(this).attr("header") ? "&fh=1" : "") + ("true" == jQuery(this).attr("transparent") ? "&transparent=1" : "") + "&code=" + jQuery(this).attr("code") + (isSafari && s ? "&ct=" + s : "") + (isSafari && !urlCtV ? "&sh=" + getc("sh") : "") + "&eref=" + encodeURIComponent(eref);
                        backFromStripe && (erefQ = eref.split("?")[1], erefQ && (erefQ = erefQ.replace(new RegExp("&code=", "g"), "&c="), erefQ = erefQ.replace(new RegExp("&ct=", "g"), "&cto=")), o += erefQ), console.log("scoutsssDialogUrl"), console.log(o), container.html('<div class="scoutsss-dialog-header"><div class="scoutsss-dialog-refresh sd-controls"><img class="sd-icon" width="30" src="https://business.scoutsss.com/images/refresh.png" /></div><div data-code="' + jQuery(this).attr("code") + '" data-onclose="' + jQuery(this).attr("onclose") + '" class="scoutsss-dialog-close sd-controls"><img class="sd-icon" width="30" src="https://business.scoutsss.com/images/close.png" /></div></div><center><img style="display:none;" class="container-loader" src="https://business.scoutsss.com/images/typing.png" /><iframe ' + ("true" == jQuery(this).attr("transparent") ? 'allowtransparency="true"' : "") + ' name="scoutsssFormTarget-' + jQuery(this).attr("code") + '" id="scoutsssFormTarget-' + jQuery(this).attr("code") + '" frameborder="0" width="100%" height="' + (height - 46) + '" src="' + o + '"></iframe></center>'), container.find(".sd-controls").css({
                            display: "inline-block",
                            margin: "5px"
                        }), container.find(".scoutsss-dialog-header").css({
                            "text-align": "right",
                            padding: "3px"
                        }), container.find(".scoutsss-dialog-close, .scoutsss-dialog-refresh").css("cursor", "pointer"), container.attr("id", jQuery(this).attr("id") + "-container"), jQuery("body").append(container), container.find(".container-loader").show(), container.find("iframe").on("load", function() {
                            jQuery(this).closest(".scoutsss-dialog-container").find(".container-loader").hide(), jQuery(this).show()
                        }), "true" != jQuery(this).attr("draggable") || isMobile || jQuery("#" + jQuery(this).attr("id") + "-container").draggable()
                    } else jQuery("#" + jQuery(this).attr("id") + "-container").show()
                }), jQuery("body").append(btn), 1 == backFromStripe && btn.trigger("click", [!0])
            }
            btn && (isClosed = getc("closed-" + btn.attr("code")), "1" == isClosed && "0B1601" == btn.attr("code") && (btn.css("background", ""), btn.find("div").hide(), btn.find("img").parent().show()))
        }), jQuery(".scoutsss-dialog-btn[hidden='true']").hide()
    })
}
function scoutsssDialogsGetPlacement(t) {
    var e = {};
    return "top-left" == t && (e = {
        left: isMobile ? "0px" : "40px",
        top: isMobile ? "0px" : "100px"
    }), "top-right" == t && (e = {
        right: isMobile ? "0px" : "40px",
        top: isMobile ? "0px" : "100px"
    }), "bottom-left" == t && (e = {
        left: isMobile ? "0px" : "40px",
        bottom: isMobile ? "16px" : "100px"
    }), "bottom-right" == t && (e = {
        right: isMobile ? "0px" : "40px",
        bottom: isMobile ? "16px" : "100px"
    }), "top-centered" == t && (e = {
        right: "0px",
        left: "0px",
        top: "50px",
        "margin-right": "auto",
        "margin-left": "auto"
    }), "bottom-centered" == t && (e = {
        right: "0px",
        left: "0px",
        bottom: "50px",
        "margin-right": "auto",
        "margin-left": "auto"
    }), "left-centered" == t && (e = {
        left: "50px",
        top: "0px",
        height: "20px",
        bottom: "0px",
        "margin-top": "auto",
        "margin-bottom": "auto"
    }), "right-centered" == t && (e = {
        right: "0px",
        top: "0px",
        height: "20px",
        bottom: "0px",
        "margin-top": "auto",
        "margin-bottom": "auto"
    }), "centered" == t && (e = {
        right: "0px",
        left: "0px",
        top: "0px",
        height: "20px",
        bottom: "0px",
        "margin-right": "auto",
        "margin-left": "auto",
        "margin-top": "auto",
        "margin-bottom": "auto"
    }), e
}
function setc(t, e, i) {
    var s = t,
        o = new Date;
    o.setTime(o.getTime() + 24 * i * 60 * 60 * 1e3);
    var n = "expires=" + o.toUTCString();
    console.log("name %s", t), document.cookie = s + "=" + e + ";" + n + ";path=/"
}
function setct(t, e) {
    setc("ct", t, e)
}
function getc(t) {
    for (var e = t, i = e + "=", s = document.cookie.split(";"), o = 0; o < s.length; o++) {
        for (var n = s[o];
        " " == n.charAt(0);) n = n.substring(1);
        if (0 == n.indexOf(i)) return n.substring(i.length, n.length)
    }
    return ""
}
function getct() {
    return getc("ct")
}
function loadjQueryUI() {
    if (void 0 === jQuery.ui) {
        var t = document.getElementsByTagName("head")[0],
            e = document.createElement("script");
        e.type = "text/javascript", e.src = "//ajax.googleapis.com/ajax/libs/jqueryui/1.12.1/jquery-ui.min.js", e.onload = scoutsssDialogsInit, t.appendChild(e)
    } else scoutsssDialogsInit()
}
var isMobile = /Android|webOS|iPhone|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent),
    isSafari = navigator.userAgent.search("Safari") >= 0 && navigator.userAgent.search("Chrome") < 0,
    webUrl = "https://business.scoutsss.com",
    eref = window.location.href,
    autoOpen = !1,
    backFromStripe = eref.indexOf("&stripe=1&") > -1 && eref.indexOf("&session_id=") > -1 && eref.indexOf("&userJobId=") > -1 && eref.indexOf("?") > -1,
    urlCt = eref.split("&ct="),
    urlCtV;
if (urlCt[1] && isSafari) {
    var urlCtPStr = new String(urlCt[1]);
    urlCtP = urlCtPStr.split("&"), urlCtV = urlCtP[0]
}
if (window.location.href.includes("test.scoutsss") && (webUrl = "https://test.scoutsss.com"), window.location.href.includes("local") && (webUrl = "http://localhost"), "undefined" == typeof jQuery) {
    var headTag = document.getElementsByTagName("head")[0],
        jqTag = document.createElement("script");
    jqTag.type = "text/javascript", jqTag.src = "//ajax.googleapis.com/ajax/libs/jquery/3.2.1/jquery.min.js", jqTag.onload = loadjQueryUI, headTag.appendChild(jqTag)
} else void 0 === jQuery.ui ? loadjQueryUI() : scoutsssDialogsInit();