(ns lanterna-magica.bp
  "Reagent wrappers for Blueprint.js React components."
  (:require ["@blueprintjs/core" :as bp]
            ["@blueprintjs/select" :as bp-select]
            [reagent.core :as r]))

(def button          (r/adapt-react-class bp/Button))
(def callout         (r/adapt-react-class bp/Callout))
(def dialog          (r/adapt-react-class bp/Dialog))
(def dialog-body     (r/adapt-react-class bp/DialogBody))
(def dialog-footer   (r/adapt-react-class bp/DialogFooter))
(def icon            (r/adapt-react-class bp/Icon))
(def input-group     (r/adapt-react-class bp/InputGroup))
(def navbar          (r/adapt-react-class bp/Navbar))
(def navbar-group    (r/adapt-react-class bp/NavbarGroup))
(def navbar-heading  (r/adapt-react-class bp/NavbarHeading))
(def navbar-divider  (r/adapt-react-class bp/NavbarDivider))
(def non-ideal-state (r/adapt-react-class bp/NonIdealState))
(def spinner         (r/adapt-react-class bp/Spinner))
(def switch-control  (r/adapt-react-class bp/Switch))
(def tag             (r/adapt-react-class bp/Tag))

;; @blueprintjs/select
(def select-component bp-select/Select)
(def menu-item       (r/adapt-react-class bp/MenuItem))
