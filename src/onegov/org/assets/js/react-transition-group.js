!function(e,t){"object"==typeof exports&&"object"==typeof module?module.exports=t(require("react"),require("react-dom")):"function"==typeof define&&define.amd?define(["react","react-dom"],t):"object"==typeof exports?exports.ReactTransitionGroup=t(require("react"),require("react-dom")):e.ReactTransitionGroup=t(e.React,e.ReactDOM)}(this,function(e,t){return function(e){function t(r){if(n[r])return n[r].exports;var o=n[r]={i:r,l:!1,exports:{}};return e[r].call(o.exports,o,o.exports,t),o.l=!0,o.exports}var n={};return t.m=e,t.c=n,t.i=function(e){return e},t.d=function(e,n,r){t.o(e,n)||Object.defineProperty(e,n,{configurable:!1,enumerable:!0,get:r})},t.n=function(e){var n=e&&e.__esModule?function(){return e.default}:function(){return e};return t.d(n,"a",n),n},t.o=function(e,t){return Object.prototype.hasOwnProperty.call(e,t)},t.p="",t(t.s=17)}([function(t,n){t.exports=e},function(e,t,n){"use strict";"function"==typeof Symbol&&Symbol.iterator;e.exports=n(14)()},function(e,t,n){"use strict";function r(e){return e&&e.__esModule?e:{default:e}}function o(e,t){if(!(e instanceof t))throw new TypeError("Cannot call a class as a function")}function i(e,t){if(!e)throw new ReferenceError("this hasn't been initialised - super() hasn't been called");return!t||"object"!=typeof t&&"function"!=typeof t?e:t}function a(e,t){if("function"!=typeof t&&null!==t)throw new TypeError("Super expression must either be null or a function, not "+typeof t);e.prototype=Object.create(t&&t.prototype,{constructor:{value:e,enumerable:!1,writable:!0,configurable:!0}}),t&&(Object.setPrototypeOf?Object.setPrototypeOf(e,t):e.__proto__=t)}t.__esModule=!0;var u=Object.assign||function(e){for(var t=1;t<arguments.length;t++){var n=arguments[t];for(var r in n)Object.prototype.hasOwnProperty.call(n,r)&&(e[r]=n[r])}return e},s=n(6),l=r(s),c=n(0),p=r(c),f=n(1),d=r(f),m=n(15),h=(r(m),n(18)),y=(d.default.any,d.default.func,d.default.node,{component:"span",childFactory:function(e){return e}}),v=function(e){function t(n,r){o(this,t);var a=i(this,e.call(this,n,r));return a.performAppear=function(e,t){a.currentlyTransitioningKeys[e]=!0,t.componentWillAppear?t.componentWillAppear(a._handleDoneAppearing.bind(a,e,t)):a._handleDoneAppearing(e,t)},a._handleDoneAppearing=function(e,t){t.componentDidAppear&&t.componentDidAppear(),delete a.currentlyTransitioningKeys[e];var n=(0,h.getChildMapping)(a.props.children);n&&n.hasOwnProperty(e)||a.performLeave(e,t)},a.performEnter=function(e,t){a.currentlyTransitioningKeys[e]=!0,t.componentWillEnter?t.componentWillEnter(a._handleDoneEntering.bind(a,e,t)):a._handleDoneEntering(e,t)},a._handleDoneEntering=function(e,t){t.componentDidEnter&&t.componentDidEnter(),delete a.currentlyTransitioningKeys[e];var n=(0,h.getChildMapping)(a.props.children);n&&n.hasOwnProperty(e)||a.performLeave(e,t)},a.performLeave=function(e,t){a.currentlyTransitioningKeys[e]=!0,t.componentWillLeave?t.componentWillLeave(a._handleDoneLeaving.bind(a,e,t)):a._handleDoneLeaving(e,t)},a._handleDoneLeaving=function(e,t){t.componentDidLeave&&t.componentDidLeave(),delete a.currentlyTransitioningKeys[e];var n=(0,h.getChildMapping)(a.props.children);n&&n.hasOwnProperty(e)?a.keysToEnter.push(e):a.setState(function(t){var n=u({},t.children);return delete n[e],{children:n}})},a.childRefs=Object.create(null),a.state={children:(0,h.getChildMapping)(n.children)},a}return a(t,e),t.prototype.componentWillMount=function(){this.currentlyTransitioningKeys={},this.keysToEnter=[],this.keysToLeave=[]},t.prototype.componentDidMount=function(){var e=this.state.children;for(var t in e)e[t]&&this.performAppear(t,this.childRefs[t])},t.prototype.componentWillReceiveProps=function(e){var t=(0,h.getChildMapping)(e.children),n=this.state.children;this.setState({children:(0,h.mergeChildMappings)(n,t)});for(var r in t){var o=n&&n.hasOwnProperty(r);!t[r]||o||this.currentlyTransitioningKeys[r]||this.keysToEnter.push(r)}for(var i in n){var a=t&&t.hasOwnProperty(i);!n[i]||a||this.currentlyTransitioningKeys[i]||this.keysToLeave.push(i)}},t.prototype.componentDidUpdate=function(){var e=this,t=this.keysToEnter;this.keysToEnter=[],t.forEach(function(t){return e.performEnter(t,e.childRefs[t])});var n=this.keysToLeave;this.keysToLeave=[],n.forEach(function(t){return e.performLeave(t,e.childRefs[t])})},t.prototype.render=function(){var e=this,t=[];for(var n in this.state.children)!function(n){var r=e.state.children[n];if(r){var o="string"!=typeof r.ref,i=e.props.childFactory(r),a=function(t){e.childRefs[n]=t};i===r&&o&&(a=(0,l.default)(r.ref,a)),t.push(p.default.cloneElement(i,{key:n,ref:a}))}}(n);var r=u({},this.props);return delete r.transitionLeave,delete r.transitionName,delete r.transitionAppear,delete r.transitionEnter,delete r.childFactory,delete r.transitionLeaveTimeout,delete r.transitionEnterTimeout,delete r.transitionAppearTimeout,delete r.component,p.default.createElement(this.props.component,r,t)},t}(p.default.Component);v.displayName="TransitionGroup",v.propTypes={},v.defaultProps=y,t.default=v,e.exports=t.default},function(e,t,n){"use strict";Object.defineProperty(t,"__esModule",{value:!0}),t.default=!("undefined"==typeof window||!window.document||!window.document.createElement),e.exports=t.default},function(e,t,n){"use strict";function r(e){return e&&e.__esModule?e:{default:e}}function o(e){var t="transition"+e+"Timeout",n="transition"+e;return function(e){if(e[n]){if(null==e[t])return new Error(t+" wasn't supplied to CSSTransitionGroup: this can cause unreliable animations and won't be supported in a future version of React. See https://fb.me/react-animation-transition-group-timeout for more information.");if("number"!=typeof e[t])return new Error(t+" must be a number (in milliseconds)")}return null}}t.__esModule=!0,t.nameShape=void 0,t.transitionTimeout=o;var i=n(0),a=(r(i),n(1)),u=r(a);t.nameShape=u.default.oneOfType([u.default.string,u.default.shape({enter:u.default.string,leave:u.default.string,active:u.default.string}),u.default.shape({enter:u.default.string,enterActive:u.default.string,leave:u.default.string,leaveActive:u.default.string,appear:u.default.string,appearActive:u.default.string})])},function(e,t,n){"use strict";function r(e){return e&&e.__esModule?e:{default:e}}function o(e,t){if(!(e instanceof t))throw new TypeError("Cannot call a class as a function")}function i(e,t){if(!e)throw new ReferenceError("this hasn't been initialised - super() hasn't been called");return!t||"object"!=typeof t&&"function"!=typeof t?e:t}function a(e,t){if("function"!=typeof t&&null!==t)throw new TypeError("Super expression must either be null or a function, not "+typeof t);e.prototype=Object.create(t&&t.prototype,{constructor:{value:e,enumerable:!1,writable:!0,configurable:!0}}),t&&(Object.setPrototypeOf?Object.setPrototypeOf(e,t):e.__proto__=t)}t.__esModule=!0;var u=Object.assign||function(e){for(var t=1;t<arguments.length;t++){var n=arguments[t];for(var r in n)Object.prototype.hasOwnProperty.call(n,r)&&(e[r]=n[r])}return e},s=n(0),l=r(s),c=n(1),p=r(c),f=n(2),d=r(f),m=n(16),h=r(m),y=n(4),v=(y.nameShape.isRequired,p.default.bool,p.default.bool,p.default.bool,(0,y.transitionTimeout)("Appear"),(0,y.transitionTimeout)("Enter"),(0,y.transitionTimeout)("Leave"),{transitionAppear:!1,transitionEnter:!0,transitionLeave:!0}),g=function(e){function t(){var n,r,a;o(this,t);for(var u=arguments.length,s=Array(u),c=0;c<u;c++)s[c]=arguments[c];return n=r=i(this,e.call.apply(e,[this].concat(s))),r._wrapChild=function(e){return l.default.createElement(h.default,{name:r.props.transitionName,appear:r.props.transitionAppear,enter:r.props.transitionEnter,leave:r.props.transitionLeave,appearTimeout:r.props.transitionAppearTimeout,enterTimeout:r.props.transitionEnterTimeout,leaveTimeout:r.props.transitionLeaveTimeout},e)},a=n,i(r,a)}return a(t,e),t.prototype.render=function(){return l.default.createElement(d.default,u({},this.props,{childFactory:this._wrapChild}))},t}(l.default.Component);g.displayName="CSSTransitionGroup",g.propTypes={},g.defaultProps=v,t.default=g,e.exports=t.default},function(e,t,n){"use strict";e.exports=function(){for(var e=arguments.length,t=[],n=0;n<e;n++)t[n]=arguments[n];if(t=t.filter(function(e){return null!=e}),0!==t.length)return 1===t.length?t[0]:t.reduce(function(e,t){return function(){e.apply(this,arguments),t.apply(this,arguments)}})}},function(e,t,n){"use strict";function r(e,t){e.classList?e.classList.add(t):(0,i.default)(e)||(e.className=e.className+" "+t)}Object.defineProperty(t,"__esModule",{value:!0}),t.default=r;var o=n(8),i=function(e){return e&&e.__esModule?e:{default:e}}(o);e.exports=t.default},function(e,t,n){"use strict";function r(e,t){return e.classList?!!t&&e.classList.contains(t):-1!==(" "+e.className+" ").indexOf(" "+t+" ")}Object.defineProperty(t,"__esModule",{value:!0}),t.default=r,e.exports=t.default},function(e,t,n){"use strict";e.exports=function(e,t){e.classList?e.classList.remove(t):e.className=e.className.replace(new RegExp("(^|\\s)"+t+"(?:\\s|$)","g"),"$1").replace(/\s+/g," ").replace(/^\s*|\s*$/g,"")}},function(e,t,n){"use strict";Object.defineProperty(t,"__esModule",{value:!0}),t.animationEnd=t.animationDelay=t.animationTiming=t.animationDuration=t.animationName=t.transitionEnd=t.transitionDuration=t.transitionDelay=t.transitionTiming=t.transitionProperty=t.transform=void 0;var r=n(3),o=function(e){return e&&e.__esModule?e:{default:e}}(r),i="transform",a=void 0,u=void 0,s=void 0,l=void 0,c=void 0,p=void 0,f=void 0,d=void 0,m=void 0,h=void 0,y=void 0;if(o.default){var v=function(){for(var e=document.createElement("div").style,t={O:function(e){return"o"+e.toLowerCase()},Moz:function(e){return e.toLowerCase()},Webkit:function(e){return"webkit"+e},ms:function(e){return"MS"+e}},n=Object.keys(t),r=void 0,o=void 0,i="",a=0;a<n.length;a++){var u=n[a];if(u+"TransitionProperty"in e){i="-"+u.toLowerCase(),r=t[u]("TransitionEnd"),o=t[u]("AnimationEnd");break}}return!r&&"transitionProperty"in e&&(r="transitionend"),!o&&"animationName"in e&&(o="animationend"),e=null,{animationEnd:o,transitionEnd:r,prefix:i}}();a=v.prefix,t.transitionEnd=u=v.transitionEnd,t.animationEnd=s=v.animationEnd,t.transform=i=a+"-"+i,t.transitionProperty=l=a+"-transition-property",t.transitionDuration=c=a+"-transition-duration",t.transitionDelay=f=a+"-transition-delay",t.transitionTiming=p=a+"-transition-timing-function",t.animationName=d=a+"-animation-name",t.animationDuration=m=a+"-animation-duration",t.animationTiming=h=a+"-animation-delay",t.animationDelay=y=a+"-animation-timing-function"}t.transform=i,t.transitionProperty=l,t.transitionTiming=p,t.transitionDelay=f,t.transitionDuration=c,t.transitionEnd=u,t.animationName=d,t.animationDuration=m,t.animationTiming=h,t.animationDelay=y,t.animationEnd=s,t.default={transform:i,end:u,property:l,timing:p,delay:f,duration:c}},function(e,t,n){"use strict";function r(e){var t=(new Date).getTime(),n=Math.max(0,16-(t-p)),r=setTimeout(e,n);return p=t,r}Object.defineProperty(t,"__esModule",{value:!0});var o=n(3),i=function(e){return e&&e.__esModule?e:{default:e}}(o),a=["","webkit","moz","o","ms"],u="clearTimeout",s=r,l=void 0,c=function(e,t){return e+(e?t[0].toUpperCase()+t.substr(1):t)+"AnimationFrame"};i.default&&a.some(function(e){var t=c(e,"request");if(t in window)return u=c(e,"cancel"),s=function(e){return window[t](e)}});var p=(new Date).getTime();l=function(e){return s(e)},l.cancel=function(e){window[u]&&"function"==typeof window[u]&&window[u](e)},t.default=l,e.exports=t.default},function(e,t,n){"use strict";function r(e){return function(){return e}}var o=function(){};o.thatReturns=r,o.thatReturnsFalse=r(!1),o.thatReturnsTrue=r(!0),o.thatReturnsNull=r(null),o.thatReturnsThis=function(){return this},o.thatReturnsArgument=function(e){return e},e.exports=o},function(e,t,n){"use strict";function r(e,t,n,r,i,a,u,s){if(o(t),!e){var l;if(void 0===t)l=new Error("Minified exception occurred; use the non-minified dev environment for the full error message and additional helpful warnings.");else{var c=[n,r,i,a,u,s],p=0;l=new Error(t.replace(/%s/g,function(){return c[p++]})),l.name="Invariant Violation"}throw l.framesToPop=1,l}}var o=function(e){};e.exports=r},function(e,t,n){"use strict";var r=n(12),o=n(13);e.exports=function(){function e(){o(!1)}function t(){return e}e.isRequired=e;var n={array:e,bool:e,func:e,number:e,object:e,string:e,symbol:e,any:e,arrayOf:t,element:e,instanceOf:t,node:e,objectOf:t,oneOf:t,oneOfType:t,shape:t};return n.checkPropTypes=r,n.PropTypes=n,n}},function(e,t,n){"use strict";var r=function(){};e.exports=r},function(e,t,n){"use strict";function r(e){return e&&e.__esModule?e:{default:e}}function o(e,t){if(!(e instanceof t))throw new TypeError("Cannot call a class as a function")}function i(e,t){if(!e)throw new ReferenceError("this hasn't been initialised - super() hasn't been called");return!t||"object"!=typeof t&&"function"!=typeof t?e:t}function a(e,t){if("function"!=typeof t&&null!==t)throw new TypeError("Super expression must either be null or a function, not "+typeof t);e.prototype=Object.create(t&&t.prototype,{constructor:{value:e,enumerable:!1,writable:!0,configurable:!0}}),t&&(Object.setPrototypeOf?Object.setPrototypeOf(e,t):e.__proto__=t)}function u(e,t){return w.length?w.forEach(function(n){return e.addEventListener(n,t,!1)}):setTimeout(t,0),function(){w.length&&w.forEach(function(n){return e.removeEventListener(n,t,!1)})}}t.__esModule=!0;var s=Object.assign||function(e){for(var t=1;t<arguments.length;t++){var n=arguments[t];for(var r in n)Object.prototype.hasOwnProperty.call(n,r)&&(e[r]=n[r])}return e},l=n(7),c=r(l),p=n(9),f=r(p),d=n(11),m=r(d),h=n(10),y=n(0),v=r(y),g=n(1),T=r(g),b=n(19),E=n(4),w=[];h.transitionEnd&&w.push(h.transitionEnd),h.animationEnd&&w.push(h.animationEnd);var _=(T.default.node,E.nameShape.isRequired,T.default.bool,T.default.bool,T.default.bool,T.default.number,T.default.number,T.default.number,function(e){function t(){var n,r,a;o(this,t);for(var u=arguments.length,s=Array(u),l=0;l<u;l++)s[l]=arguments[l];return n=r=i(this,e.call.apply(e,[this].concat(s))),r.componentWillAppear=function(e){r.props.appear?r.transition("appear",e,r.props.appearTimeout):e()},r.componentWillEnter=function(e){r.props.enter?r.transition("enter",e,r.props.enterTimeout):e()},r.componentWillLeave=function(e){r.props.leave?r.transition("leave",e,r.props.leaveTimeout):e()},a=n,i(r,a)}return a(t,e),t.prototype.componentWillMount=function(){this.classNameAndNodeQueue=[],this.transitionTimeouts=[]},t.prototype.componentWillUnmount=function(){this.unmounted=!0,this.timeout&&clearTimeout(this.timeout),this.transitionTimeouts.forEach(function(e){clearTimeout(e)}),this.classNameAndNodeQueue.length=0},t.prototype.transition=function(e,t,n){var r=(0,b.findDOMNode)(this);if(!r)return void(t&&t());var o=this.props.name[e]||this.props.name+"-"+e,i=this.props.name[e+"Active"]||o+"-active",a=null,s=void 0;(0,c.default)(r,o),this.queueClassAndNode(i,r);var l=function(e){e&&e.target!==r||(clearTimeout(a),s&&s(),(0,f.default)(r,o),(0,f.default)(r,i),s&&s(),t&&t())};n?(a=setTimeout(l,n),this.transitionTimeouts.push(a)):h.transitionEnd&&(s=u(r,l))},t.prototype.queueClassAndNode=function(e,t){var n=this;this.classNameAndNodeQueue.push({className:e,node:t}),this.rafHandle||(this.rafHandle=(0,m.default)(function(){return n.flushClassNameAndNodeQueue()}))},t.prototype.flushClassNameAndNodeQueue=function(){this.unmounted||this.classNameAndNodeQueue.forEach(function(e){e.node.scrollTop,(0,c.default)(e.node,e.className)}),this.classNameAndNodeQueue.length=0,this.rafHandle=null},t.prototype.render=function(){var e=s({},this.props);return delete e.name,delete e.appear,delete e.enter,delete e.leave,delete e.appearTimeout,delete e.enterTimeout,delete e.leaveTimeout,delete e.children,v.default.cloneElement(v.default.Children.only(this.props.children),e)},t}(v.default.Component));_.displayName="CSSTransitionGroupChild",_.propTypes={},t.default=_,e.exports=t.default},function(e,t,n){"use strict";function r(e){return e&&e.__esModule?e:{default:e}}var o=n(5),i=r(o),a=n(2),u=r(a);e.exports={TransitionGroup:u.default,CSSTransitionGroup:i.default}},function(e,t,n){"use strict";function r(e){if(!e)return e;var t={};return i.Children.map(e,function(e){return e}).forEach(function(e){t[e.key]=e}),t}function o(e,t){function n(n){return t.hasOwnProperty(n)?t[n]:e[n]}e=e||{},t=t||{};var r={},o=[];for(var i in e)t.hasOwnProperty(i)?o.length&&(r[i]=o,o=[]):o.push(i);var a=void 0,u={};for(var s in t){if(r.hasOwnProperty(s))for(a=0;a<r[s].length;a++){var l=r[s][a];u[r[s][a]]=n(l)}u[s]=n(s)}for(a=0;a<o.length;a++)u[o[a]]=n(o[a]);return u}t.__esModule=!0,t.getChildMapping=r,t.mergeChildMappings=o;var i=n(0)},function(e,n){e.exports=t}])});