resource "proxmox_lxc" "mayl_home" {
  target_node  = var.proxmox_target_node
  hostname     = var.container_hostname
  ostemplate   = "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
  password     = "ChangeMe123!"
  unprivileged = true
  start        = true

  rootfs {
    storage = "local-lvm"
    size    = var.container_disk
  }

  network {
    name   = "eth0"
    bridge = "vmbr0"
    ip     = var.container_ip
    gw     = var.gateway
  }

  cores  = var.container_cores
  memory = var.container_memory
  swap   = 512

  features {
    nesting = true
  }

  description = "mayl-home — Email archiver with AI classification (Ollama + Flask)"
}
